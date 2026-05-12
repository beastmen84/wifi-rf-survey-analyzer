from tests._common import *

class LiveMapDataLogicTests(unittest.TestCase):
    def test_map_config_normalizes_interference_without_changing_other_maps(self):
        interference_config = MapConfig(
            map_type="interference",
            band="all",
            point_label_mode="all",
        ).normalized()
        signal_config = MapConfig(
            map_type="signal",
            band="all",
            point_label_mode="all",
        ).normalized()

        self.assertEqual(interference_config.band, "2.4")
        self.assertEqual(interference_config.point_label_mode, "critical")
        self.assertEqual(signal_config.band, "all")
        self.assertEqual(signal_config.point_label_mode, "all")

    def test_channel_payload_ap_group_filter_applies_before_strongest_selection(self):
        selected_bssid = "70:4f:57:aa:bb:10"
        stronger_bssid = "90:11:22:33:44:10"
        groups = [
            build_manual_ap_group("selected-ap", [selected_bssid]),
            build_manual_ap_group("stronger-ap", [stronger_bssid]),
        ]
        group_map = serialize_ap_group_map(build_bssid_to_manual_group_map(groups))
        role_map = serialize_ap_group_roles(build_ap_group_role_map(groups))
        selected_row = build_row("p1", "MAIN", selected_bssid, -70, 1)
        stronger_row = build_row("p1", "MAIN", stronger_bssid, -40, 6)
        rows = rows_to_dataframe([selected_row, stronger_row])

        unfiltered = build_channel_payload(
            rows,
            MapConfig(
                ssid="MAIN",
                band="2.4",
                map_type="channel",
                point_label_mode="all",
                ap_group_map=group_map,
                ap_group_roles=role_map,
            ),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )
        filtered = build_channel_payload(
            rows,
            MapConfig(
                ssid="MAIN",
                band="2.4",
                map_type="channel",
                point_label_mode="all",
                ap_group_filter="selected-ap",
                ap_group_map=group_map,
                ap_group_roles=role_map,
            ),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )

        self.assertIn("CH 6", unfiltered["point_infos"][0]["legend_label"])
        self.assertIn("CH 1", filtered["point_infos"][0]["legend_label"])
        self.assertEqual(filtered["point_infos"][0]["legend_label"], filtered["scale_payload"]["items"][0]["label"])

    def test_interference_intra_ssid_ignores_other_ssids_while_all_counts_them(self):
        serving_bssid = "70:4f:57:aa:bb:10"
        neighbor_bssid = "90:11:22:33:44:10"
        rows = [
            build_row("p1", "MAIN", serving_bssid, -50, 1),
            build_row("p1", "NEIGHBOR", neighbor_bssid, -45, 1),
        ]
        df = rows_to_dataframe(rows)

        intra = calculate_interference_points(
            df,
            "MAIN",
            "2.4",
            mode="intra_ssid",
            include_details=True,
        )
        all_networks = calculate_interference_points(
            df,
            "MAIN",
            "2.4",
            mode="all",
            include_details=True,
        )

        self.assertEqual(intra.iloc[0]["risk"], 0)
        self.assertEqual(intra.iloc[0]["interferer_count"], 0)
        self.assertGreater(all_networks.iloc[0]["risk"], 0)
        self.assertEqual(all_networks.iloc[0]["strongest_interferer_bssid"], neighbor_bssid)


class LiveRendererCacheTests(unittest.TestCase):
    def tearDown(self):
        with live_renderer_module._cache_lock:
            live_renderer_module._result_cache.clear()

    def test_clone_cached_result_does_not_share_nested_payloads(self):
        cached = {
            "image": Image.new("RGB", (4, 4), "white"),
            "point_infos": [
                {
                    "x": 10.0,
                    "selection": {"active": False},
                }
            ],
            "scale_payload": {
                "kind": "swatches",
                "items": [{"label": "AP 1", "selected": False}],
            },
        }

        first = clone_cached_result(cached)
        first["point_infos"][0]["x"] = 99.0
        first["point_infos"][0]["selection"]["active"] = True
        first["scale_payload"]["items"][0]["label"] = "mutated"
        first["scale_payload"]["items"][0]["selected"] = True

        second = clone_cached_result(cached)

        self.assertEqual(second["point_infos"][0]["x"], 10.0)
        self.assertFalse(second["point_infos"][0]["selection"]["active"])
        self.assertEqual(second["scale_payload"]["items"][0]["label"], "AP 1")
        self.assertFalse(second["scale_payload"]["items"][0]["selected"])
        self.assertIsNot(second["image"], cached["image"])

    def test_cached_continuous_render_returns_independent_point_infos(self):
        rows = []
        for point_id, x, y, signal, bssid in (
            ("p1", "10", "10", -45, "70:4f:57:aa:bb:10"),
            ("p2", "70", "12", -60, "70:4f:57:aa:bb:11"),
            ("p3", "35", "52", -72, "70:4f:57:aa:bb:12"),
        ):
            row = build_row(point_id, "MAIN", bssid, signal, 1)
            row["x"] = x
            row["y"] = y
            rows.append(row)
        df = rows_to_dataframe(rows)
        config = MapConfig(
            ssid="MAIN",
            band="2.4",
            map_type="signal",
            interpolation="linear",
            smoothing_sigma=0,
            max_distance_px=200,
        )
        bg_image = Image.new("RGB", (80, 60), "white")
        translations = {"signal_title": "Signal"}

        first = render_live_continuous_map(
            df,
            config,
            bg_image,
            translations,
            lambda map_type, row, total: f"{map_type}:{row['x']},{row['y']}",
            lambda grid_z, map_config: (-90, -30),
        )
        self.assertIsNotNone(first)
        first["point_infos"][0]["color"] = "#ff00ff"
        first["point_infos"][0]["tooltip"] = "mutated"

        second = render_live_continuous_map(
            df,
            config,
            bg_image,
            translations,
            lambda map_type, row, total: f"{map_type}:{row['x']},{row['y']}",
            lambda grid_z, map_config: (-90, -30),
        )

        self.assertEqual(second["point_infos"][0]["color"], "#111111")
        self.assertNotEqual(second["point_infos"][0]["tooltip"], "mutated")
        self.assertIsNot(second["image"], first["image"])

    def test_stable_dataframe_fingerprint_tracks_render_inputs(self):
        row = build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1)
        df = rows_to_dataframe([row])
        same_render_inputs = df.copy()
        same_render_inputs["ui_only"] = "expanded"
        changed_signal = df.copy()
        changed_signal.loc[0, "signal_dbm"] = -65
        changed_frequency = df.copy()
        changed_frequency.loc[0, "frequency_mhz"] = "5975"

        self.assertEqual(
            stable_dataframe_fingerprint(df),
            stable_dataframe_fingerprint(same_render_inputs),
        )
        self.assertNotEqual(
            stable_dataframe_fingerprint(df),
            stable_dataframe_fingerprint(changed_signal),
        )
        self.assertNotEqual(
            stable_dataframe_fingerprint(df),
            stable_dataframe_fingerprint(changed_frequency),
        )



class FloorplanViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_survey_point_tooltip_uses_live_style_html_layout(self):
        tooltip = format_point_tooltip(
            {
                "x": 10,
                "y": 20,
                "best_signal_dbm": -61,
                "signal_scope": "relevant",
                "row_count": 4,
                "relevant_row_count": 2,
                "timestamp": "2026-05-11T12:00:00",
                "ssids": ["MAIN", "Guest <wifi>"],
            }
        )

        self.assertIn("<table", tooltip)
        self.assertIn("border-left:4px solid", tooltip)
        self.assertIn("Survey point", tooltip)
        self.assertIn("Best signal", tooltip)
        self.assertIn("Guest &lt;wifi&gt;", tooltip)

    def test_survey_ap_tooltip_uses_live_style_html_layout(self):
        tooltip = format_ap_tooltip(
            {"group_id": "office", "bssids": ["70:4f:57:aa:bb:10"]},
            "Office AP",
            30,
            40,
        )

        self.assertIn("<table", tooltip)
        self.assertIn("AP position", tooltip)
        self.assertIn("Office AP", tooltip)
        self.assertIn("70:4f:57:aa:bb:10", tooltip)

    def test_ap_marker_keeps_high_resolution_source_pixmap(self):
        view = FloorplanView()

        marker = view.create_ap_marker(100, 120, {"group_id": "ap"}, "AP")
        pixmap = marker.pixmap()
        rendered_size = max(pixmap.width(), pixmap.height()) * marker.scale()

        self.assertGreater(max(pixmap.width(), pixmap.height()), AP_MARKER_BASE_SIZE)
        self.assertAlmostEqual(rendered_size, AP_MARKER_BASE_SIZE, delta=0.1)
        view.deleteLater()


class LiveMapViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_live_marker_uses_scene_sized_survey_marker(self):
        view = LiveMapView()

        marker = view.create_marker_item({})

        self.assertEqual(marker.rect().width(), LIVE_POINT_MARKER_BASE_SIZE)
        self.assertFalse(marker.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.assertEqual(view.dragMode(), QGraphicsView.DragMode.NoDrag)
        view.deleteLater()

    def test_gradient_legend_paints_payload(self):
        widget = LiveGradientLegendWidget()
        widget.resize(220, 260)
        widget.set_scale_payload({
            "kind": "gradient",
            "cmap": "RdYlGn",
            "min": -90,
            "max": -40,
            "suffix": " dBm",
        })
        pixmap = QPixmap(widget.size())
        pixmap.fill(Qt.GlobalColor.transparent)

        widget.render(pixmap)

        self.assertFalse(pixmap.isNull())
        image = pixmap.toImage()
        top = image.pixelColor(20, 20)
        middle = image.pixelColor(20, 130)
        bottom = image.pixelColor(20, 240)
        self.assertGreater(top.green(), 150)
        self.assertLess(top.red(), 90)
        self.assertGreater(middle.red(), 220)
        self.assertGreater(middle.green(), 190)
        self.assertLess(middle.blue(), 95)
        self.assertGreater(bottom.red(), 190)
        self.assertLess(bottom.green(), 120)
        widget.deleteLater()

    def test_gradient_scale_uses_saturated_heatmap_stops(self):
        self.assertEqual(
            gradient_stops("RdYlGn"),
            (
                (0.0, "#25a865"),
                (0.5, "#f2d33b"),
                (1.0, "#d94343"),
            ),
        )
        self.assertEqual(
            gradient_stops("RdYlGn_r"),
            (
                (0.0, "#d94343"),
                (0.5, "#f2d33b"),
                (1.0, "#25a865"),
            ),
        )

    def test_live_view_hosts_compact_gradient_overlay(self):
        view = LiveMapView()
        view.resize(500, 360)

        view.set_gradient_legend({
            "kind": "gradient",
            "cmap": "RdYlGn",
            "min": -90,
            "max": -40,
            "suffix": " dBm",
        })

        self.assertFalse(view.gradient_legend.isHidden())
        self.assertLessEqual(view.gradient_legend.width(), 128)
        self.assertGreaterEqual(view.gradient_legend.width(), 112)
        self.assertGreaterEqual(
            view.gradient_legend.x(),
            view.viewport().width() - view.gradient_legend.width() - 20,
        )
        self.assertGreaterEqual(
            view.gradient_legend.y(),
            view.viewport().height() - view.gradient_legend.height() - 20,
        )

        view.clear_gradient_legend()

        self.assertTrue(view.gradient_legend.isHidden())
        view.deleteLater()

    def test_live_gradient_overlay_reanchors_after_content_scroll(self):
        view = LiveMapView()
        view.resize(500, 360)
        view.set_gradient_legend({
            "kind": "gradient",
            "cmap": "RdYlGn",
            "min": -90,
            "max": -40,
            "suffix": " dBm",
        })
        anchored_pos = view.gradient_legend.pos()

        view.gradient_legend.move(0, 0)
        view.scrollContentsBy(24, 18)

        self.assertEqual(view.gradient_legend.pos(), anchored_pos)
        view.deleteLater()

    def test_live_pan_uses_closed_hand_cursor_only_while_dragging(self):
        if QApplication.overrideCursor() is not None:
            self.skipTest("existing override cursor would make the cursor stack ambiguous")

        view = LiveMapView()
        view.begin_pan(QPoint(10, 10))
        try:
            override_cursor = QApplication.overrideCursor()
            self.assertEqual(view.viewport().cursor().shape(), Qt.CursorShape.ClosedHandCursor)
            self.assertIsNotNone(override_cursor)
            self.assertEqual(override_cursor.shape(), Qt.CursorShape.ClosedHandCursor)
        finally:
            view.end_pan()

        self.assertEqual(view.viewport().cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertIsNone(QApplication.overrideCursor())
        view.deleteLater()

    def test_live_view_shows_positioned_ap_markers(self):
        view = LiveMapView()
        payload = {
            "image": Image.new("RGB", (120, 90), "white"),
            "point_infos": [],
            "ap_infos": [{"x": 40, "y": 30, "label": "AP", "tooltip": "AP"}],
        }

        view.set_payload(payload)

        self.assertEqual(len(view.ap_marker_items), 1)
        view.deleteLater()

    def test_live_signal_tooltip_rows_keep_selected_ssid_after_aggregation(self):
        rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -55, 1),
            build_row("p2", "MAIN", "70:4f:57:aa:bb:11", -65, 1),
            build_row("p3", "MAIN", "70:4f:57:aa:bb:12", -70, 1),
        ]
        for index, row in enumerate(rows):
            row["timestamp"] = f"p{index + 1}"
            row["x"] = str(20 + index * 30)
            row["y"] = str(20 + (index % 2) * 30)
        tooltip_ssids = []

        payload = build_signal_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="all", map_type="signal", interpolation="linear"),
            Image.new("RGB", (120, 90), "white"),
            {"signal_title": "Signal coverage"},
            lambda _map_type, row, _raw_rows: tooltip_ssids.append(row.get("ssid")) or "tooltip",
            lambda _grid_z, _config: (-90, -40),
        )
        payload["fig"].clf()

        self.assertEqual(tooltip_ssids, ["MAIN", "MAIN", "MAIN"])

    def test_live_interference_tooltip_hides_empty_interferer_rows(self):
        translations = {
            "interference_title": "AP interference",
            "risk": "Risk",
            "serving_ap": "Serving AP",
            "serving_channel": "Serving channel",
            "interferer": "Main interferer",
            "interferer_channel": "Interferer channel",
        }
        tooltip = build_live_tooltip(
            "interference",
            {
                "x": 10,
                "y": 20,
                "risk": 0,
                "serving_bssid": "70:4f:57:aa:bb:10",
                "serving_channel": 1,
                "strongest_interferer_bssid": "",
                "strongest_interferer_channel": "",
            },
            None,
            translations,
        )

        self.assertIn("Serving AP", tooltip)
        self.assertNotIn("Main interferer", tooltip)
        self.assertNotIn("Interferer channel", tooltip)

    def test_live_interference_tooltip_shows_interferer_rows_when_present(self):
        translations = {
            "interference_title": "AP interference",
            "risk": "Risk",
            "serving_ap": "Serving AP",
            "serving_channel": "Serving channel",
            "interferer": "Main interferer",
            "interferer_channel": "Interferer channel",
        }
        tooltip = build_live_tooltip(
            "interference",
            {
                "x": 10,
                "y": 20,
                "risk": 45,
                "serving_bssid": "70:4f:57:aa:bb:10",
                "serving_channel": 1,
                "strongest_interferer_bssid": "80:11:22:33:44:10",
                "strongest_interferer_channel": 6,
            },
            None,
            translations,
        )

        self.assertIn("Main interferer", tooltip)
        self.assertIn("Interferer channel", tooltip)
        self.assertIn("33:44:10", tooltip)

    def test_live_channel_point_labels_follow_auto_and_none_modes(self):
        rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1),
            build_row("p2", "MAIN", "70:4f:57:aa:bb:10", -52, 1),
            build_row("p3", "MAIN", "70:4f:57:aa:bb:20", -54, 6),
        ]
        payload = build_channel_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="channel", point_label_mode="auto"),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertEqual(len(payload["scale_payload"]["items"]), 2)
        self.assertEqual([item["marker_id"] for item in payload["scale_payload"]["items"]], ["channel-0", "channel-2"])

        payload = build_channel_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="channel", point_label_mode="all"),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertEqual(len(payload["scale_payload"]["items"]), 3)
        self.assertEqual([item["marker_id"] for item in payload["scale_payload"]["items"]], [
            "channel-0",
            "channel-1",
            "channel-2",
        ])

        payload = build_channel_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="channel", point_label_mode="none"),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertIsNone(payload["scale_payload"])

    def test_live_channel_all_band_labels_include_6ghz_prefix_for_ambiguous_channels(self):
        rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 5),
            build_row("p2", "MAIN", "80:11:22:33:44:10", -52, 5, band="6"),
        ]

        payload = build_channel_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="all", map_type="channel", point_label_mode="auto"),
            Image.new("RGB", (100, 100), "white"),
            {"channel_title": "AP channels"},
            {},
        )

        labels = [item["label"] for item in payload["scale_payload"]["items"]]
        self.assertEqual(labels[0].split(" - ")[0], "2.4G CH 5")
        self.assertEqual(labels[1].split(" - ")[0], "6G CH 5")

    def test_live_dominant_point_labels_follow_auto_and_none_modes(self):
        rows = [
            build_row("p1", "MAIN", "70:4f:57:aa:bb:10", -50, 1),
            build_row("p2", "MAIN", "70:4f:57:aa:bb:10", -52, 1),
            build_row("p3", "MAIN", "80:11:22:33:44:10", -54, 6),
        ]
        payload = build_dominant_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="dominant", point_label_mode="auto"),
            Image.new("RGB", (100, 100), "white"),
            {"dominant_title": "Dominant AP"},
            {},
            [],
            None,
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertEqual(len(payload["scale_payload"]["items"]), 2)
        self.assertEqual([item["marker_id"] for item in payload["scale_payload"]["items"]], [
            "dominant-0",
            "dominant-2",
        ])

        payload = build_dominant_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="dominant", point_label_mode="all"),
            Image.new("RGB", (100, 100), "white"),
            {"dominant_title": "Dominant AP"},
            {},
            [],
            None,
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertEqual(len(payload["scale_payload"]["items"]), 3)
        self.assertEqual([item["marker_id"] for item in payload["scale_payload"]["items"]], [
            "dominant-0",
            "dominant-1",
            "dominant-2",
        ])

        payload = build_dominant_payload(
            rows_to_dataframe(rows),
            MapConfig(ssid="MAIN", band="2.4", map_type="dominant", point_label_mode="none"),
            Image.new("RGB", (100, 100), "white"),
            {"dominant_title": "Dominant AP"},
            {},
            [],
            None,
        )

        self.assertFalse(any(point.get("label") for point in payload["point_infos"]))
        self.assertIsNone(payload["scale_payload"])

    def test_live_legend_marker_actions_highlight_and_focus_points(self):
        view = LiveMapView()
        try:
            view.resize(320, 240)
            view.set_payload({
                "image": Image.new("RGB", (200, 160), "white"),
                "point_infos": [
                    {"marker_id": "p1", "x": 40, "y": 50, "color": "#111111"},
                    {"marker_id": "p2", "x": 90, "y": 80, "color": "#d62728"},
                ],
                "scale_payload": None,
            })

            self.assertTrue(view.highlight_marker("p2"))
            self.assertIsNotNone(view.marker_highlight_item)
            self.assertEqual(view.marker_highlight_item.pos(), view.marker_items_by_id["p2"].scenePos())
            self.assertTrue(view.focus_marker("p1"))
            self.assertEqual(view.marker_highlight_item.pos(), view.marker_items_by_id["p1"].scenePos())
            self.assertFalse(view.highlight_marker("missing"))
        finally:
            view.deleteLater()

    def test_live_background_click_emits_only_outside_point_markers(self):
        view = LiveMapView()
        try:
            view.resize(320, 240)
            view.show()
            view.set_payload({
                "image": Image.new("RGB", (200, 160), "white"),
                "point_infos": [
                    {"marker_id": "p1", "x": 90, "y": 70, "color": "#111111"},
                ],
                "scale_payload": None,
            })
            QApplication.processEvents()

            background_clicks = []
            view.backgroundClicked.connect(lambda: background_clicks.append(True))

            marker_pos = view.mapFromScene(view.marker_items_by_id["p1"].scenePos())
            QTest.mouseClick(
                view.viewport(),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                marker_pos,
            )
            QApplication.processEvents()
            self.assertEqual(background_clicks, [])

            QTest.mouseClick(
                view.viewport(),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(5, 5),
            )
            QApplication.processEvents()
            self.assertEqual(len(background_clicks), 1)
        finally:
            view.deleteLater()

    def test_live_ap_position_markers_skip_test_groups(self):
        markers = build_ap_position_marker_infos(
            [
                {"group_id": "visible", "position": {"x": 10, "y": 20}, "role": "internal"},
                {"group_id": "hidden", "position": {"x": 30, "y": 40}, "role": "test"},
            ],
            aliases={},
            translations={},
        )

        self.assertEqual([marker["label"] for marker in markers], ["visible"])

    def test_live_ap_position_markers_highlight_selected_group(self):
        markers = build_ap_position_marker_infos(
            [{"group_id": "visible", "position": {"x": 10, "y": 20}, "role": "internal"}],
            aliases={},
            translations={},
            selected_group="visible",
        )

        self.assertTrue(markers[0]["highlight"])


class LivePdfExportTests(unittest.TestCase):
    def build_live_pdf_rows(self):
        rows = []
        for point_id, x, y, signal in (
            ("p1", "10", "10", -45),
            ("p2", "90", "20", -62),
            ("p3", "40", "80", -74),
        ):
            row = build_row(point_id, "MAIN", f"70:4f:57:aa:bb:{point_id[-1]}", signal, 6)
            row["x"] = x
            row["y"] = y
            rows.append(row)
        return rows

    def test_live_pdf_export_uses_current_config_and_writes_pdf(self):
        rows = self.build_live_pdf_rows()

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = os.path.join(temp_dir, "survey.csv")
            output_file = os.path.join(temp_dir, "chosen_live_export.pdf")
            result = generate_live_pdf_export(
                rows_to_dataframe(rows),
                Image.new("RGB", (120, 100), "white"),
                csv_file,
                MapConfig(
                    ssid="MAIN",
                    band="2.4",
                    map_type="signal",
                    interpolation="linear",
                    color_scale="auto",
                    smoothing_sigma=0,
                    max_distance_px=300,
                ),
                lambda key, **kwargs: translate("en", key, **kwargs),
                language="en",
                ap_groups=[
                    {"group_id": "ap-main", "position": {"x": 20, "y": 30}, "role": "internal"},
                ],
                output_file=output_file,
            )

            self.assertEqual(result.map_type, "signal")
            self.assertEqual(result.output_file, output_file)
            self.assertTrue(os.path.exists(result.output_file))
            with open(result.output_file, "rb") as pdf_file:
                self.assertEqual(pdf_file.read(4), b"%PDF")
            import fitz

            with fitz.open(result.output_file) as doc:
                self.assertEqual(doc[0].get_images(full=True), [])
                self.assertGreater(doc[0].get_pixmap(alpha=False).width, 0)

    def test_problem_report_pages_use_wrapped_card_layout(self):
        rows = [
            [
                f"{10 + index}, {20 + index}",
                "100.0%",
                "6",
                "6",
                (
                    "The main issue is a strong interferer on the same channel "
                    "and the diagnosis needs enough room to stay readable."
                ),
            ]
            for index in range(6)
        ]

        figures = build_problem_report_pages(
            "Problem report",
            "Wi-Fi AP interference - MAIN - 2.4 GHz",
            ["Point", "Risk", "Serving channel", "Interfering channel", "Diagnosis"],
            rows,
            "No issues",
        )
        try:
            self.assertEqual(len(figures), 2)
            first_page_text = "\n".join(text.get_text() for text in figures[0].axes[0].texts)
            self.assertIn("1/2", first_page_text)
            self.assertIn("1. Point: 10, 20", first_page_text)
            self.assertIn("Diagnosis", first_page_text)
        finally:
            for fig in figures:
                plt.close(fig)

    def test_interference_problem_report_uses_tooltip_fields(self):
        risk_df = rows_to_dataframe([
            {
                "x": 10,
                "y": 20,
                "risk": 100,
                "serving_bssid": "70:4f:57:aa:bb:10",
                "serving_ap_group": "serving-group",
                "serving_channel": 6,
                "serving_channel_width_mhz": 20,
                "strongest_interferer_bssid": "80:11:22:33:44:10",
                "strongest_interferer_ap_group": "interferer-group",
                "strongest_interferer_channel": 6,
                "strongest_interferer_channel_width_mhz": 20,
            },
            {
                "x": 30,
                "y": 40,
                "risk": 40,
                "serving_bssid": "70:4f:57:aa:bb:20",
                "serving_ap_group": "serving-group-2",
                "serving_channel": 11,
                "serving_channel_width_mhz": "",
                "strongest_interferer_bssid": "80:11:22:33:44:20",
                "strongest_interferer_ap_group": "interferer-group-2",
                "strongest_interferer_channel": 10,
                "strongest_interferer_channel_width_mhz": "",
            },
        ])

        figures = build_interference_problem_report_pages(
            risk_df,
            MapConfig(ssid="MAIN", band="2.4", map_type="interference"),
            lambda key, **kwargs: translate("en", key, **kwargs),
            "en",
            {
                "serving-group": "Serving AP",
                "interferer-group": "Neighbor AP",
            },
        )
        try:
            first_page_text = "\n".join(text.get_text() for text in figures[0].axes[0].texts)
            self.assertIn("(10, 20)", first_page_text)
            self.assertIn("Risk: 100.0%", first_page_text)
            self.assertIn("Serving AP (70:4f:57:aa:bb:10)", first_page_text)
            self.assertIn("CH 6 / 20 MHz", first_page_text)
            self.assertIn("Neighbor AP (80:11:22:33:44:10)", first_page_text)
            self.assertNotIn("Point 1", first_page_text)
            self.assertNotIn("Serving channel:", first_page_text)
            self.assertNotIn("Interfering channel:", first_page_text)
            self.assertNotIn("Diagnosis", first_page_text)
        finally:
            for fig in figures:
                plt.close(fig)

    def test_interference_problem_numbers_follow_report_order(self):
        risk_df = rows_to_dataframe([
            {"x": 10, "y": 20, "risk": 40},
            {"x": 30, "y": 40, "risk": 100},
            {"x": 50, "y": 60, "risk": 20},
        ])
        problem_df = get_interference_problem_df(risk_df)
        fig, ax = plt.subplots()
        try:
            annotate_interference_problem_numbers(ax, problem_df)
            labels = [text.get_text() for text in ax.texts]
            positions = [text.xy for text in ax.texts]

            self.assertEqual(labels, ["1", "2"])
            self.assertEqual(positions, [(30.0, 40.0), (10.0, 20.0)])
        finally:
            plt.close(fig)

    def test_channel_pdf_omits_legend_when_point_labels_are_none(self):
        fig = build_live_pdf_channel_figure(
            rows_to_dataframe(self.build_live_pdf_rows()),
            Image.new("RGB", (120, 100), "white"),
            MapConfig(ssid="MAIN", band="2.4", map_type="channel", point_label_mode="none"),
            lambda key, **kwargs: translate("en", key, **kwargs),
            "en",
            {},
            [],
        )
        try:
            side_texts = [text.get_text() for text in fig.axes[1].texts]
            self.assertNotIn("AP channels", side_texts)
            self.assertNotIn("-", side_texts)
        finally:
            plt.close(fig)

    def test_channel_pdf_legend_deduplicates_repeated_items(self):
        channel_df = rows_to_dataframe([
            {"channel": 6, "band": "2.4", "bssid": "70:4f:57:aa:bb:10", "ap_group": "ap-a"},
            {"channel": 11, "band": "2.4", "bssid": "70:4f:57:aa:bb:20", "ap_group": "ap-b"},
            {"channel": 6, "band": "2.4", "bssid": "70:4f:57:aa:bb:10", "ap_group": "ap-a"},
        ])

        items = build_channel_point_legend_items(
            channel_df,
            MapConfig(ssid="MAIN", band="2.4", map_type="channel", point_label_mode="auto"),
            {"ap-a": "AP A", "ap-b": "AP B"},
        )
        labels = [item["label"] for item in items]

        self.assertEqual(len(labels), 2)
        self.assertEqual(len(labels), len(set(labels)))
        self.assertTrue(any(label.startswith("CH 6 - AP A") for label in labels))
        self.assertTrue(any(label.startswith("CH 11 - AP B") for label in labels))

    def test_dominant_pdf_omits_legend_when_point_labels_are_none(self):
        fig, _dominant_df = build_live_pdf_dominant_figure(
            rows_to_dataframe(self.build_live_pdf_rows()),
            Image.new("RGB", (120, 100), "white"),
            MapConfig(ssid="MAIN", band="2.4", map_type="dominant", point_label_mode="none"),
            lambda key, **kwargs: translate("en", key, **kwargs),
            "en",
            {},
            [],
            None,
        )
        try:
            side_texts = [text.get_text() for text in fig.axes[1].texts]
            self.assertNotIn("Dominant AP", side_texts)
            self.assertNotIn("-", side_texts)
        finally:
            plt.close(fig)

    def test_dominant_pdf_legend_deduplicates_groups_and_uses_marker_keys(self):
        dominant_df = rows_to_dataframe([
            {
                "dominant_ap_group": "ap-a",
                "dominant_bssid": "70:4f:57:aa:bb:10",
                "roaming_overlap": False,
                "ap_position_has_warning": False,
            },
            {
                "dominant_ap_group": "ap-b",
                "dominant_bssid": "70:4f:57:aa:bb:20",
                "roaming_overlap": True,
                "ap_position_has_warning": False,
            },
            {
                "dominant_ap_group": "ap-a",
                "dominant_bssid": "70:4f:57:aa:bb:10",
                "roaming_overlap": False,
                "ap_position_has_warning": True,
            },
        ])

        items = build_dominant_point_legend_items(
            dominant_df,
            MapConfig(ssid="MAIN", band="2.4", map_type="dominant", point_label_mode="auto"),
            {"ap-a": "AP A", "ap-b": "AP B"},
            {"ap-a": "#111111", "ap-b": "#222222"},
        )
        labels = [item["label"] for item in items]
        marker_items = build_dominant_marker_legend_items(
            dominant_df,
            lambda key, **kwargs: translate("en", key, **kwargs),
        )
        marker_labels = [item["label"] for item in marker_items]

        self.assertEqual(len(labels), 2)
        self.assertEqual(sum(label.startswith("AP A") for label in labels), 1)
        self.assertEqual(sum(label.startswith("AP B") for label in labels), 1)
        self.assertEqual([item["shape"] for item in items], ["circle", "circle"])
        self.assertIn("Δ <= 5 dB", marker_labels)
        self.assertIn("Triangle = suspicious AP position", marker_labels)


