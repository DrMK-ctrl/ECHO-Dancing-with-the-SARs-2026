from echo.science_profiles import product_scope_for_record_type


def test_nisar_gcov_scope_separates_backscatter_from_interferometric_phase():
    scope = product_scope_for_record_type("ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW")

    assert scope["profile_id"] == "NISAR_L2_GCOV"
    assert scope["source_class"] == "NASA-ISRO NISAR mission SAR"
    assert "backscatter" in scope["measurement_domain"]
    assert any(item["state"] == "IMPLEMENTED_WITH_GATES" for item in scope["implemented_paths"])
    assert any("Interferometric phase" in item for item in scope["not_supported"])


def test_nisar_gunw_scope_keeps_phase_inspection_distinct_from_displacement():
    scope = product_scope_for_record_type("ECHO_GUNW_BOUNDED_PIXEL_WINDOW_REVIEW")

    assert scope["profile_id"] == "NISAR_L2_GUNW"
    assert "Phase is not displacement" in scope["measurement_domain"]
    assert "Operational displacement estimation or event interpretation." in scope["not_supported"]
    assert "GCOV comparison rules do not apply" in scope["pair_boundary"]


def test_opera_rtc_scope_preserves_sentinel1_origin_and_diagnostic_status():
    scope = product_scope_for_record_type("ECHO_OPERA_RTC_S1_PAIR_ANALYSIS")

    assert scope["profile_id"] == "OPERA_RTC_S1"
    assert "ESA Sentinel-1" in scope["source_class"]
    assert any(item["state"] == "IMPLEMENTED_DIAGNOSTIC" for item in scope["implemented_paths"])
    assert "distinct from NISAR" in scope["pair_boundary"]


def test_dswx_scope_identifies_optical_context_not_sar_validation():
    scope = product_scope_for_record_type("ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON")

    assert scope["profile_id"] == "OPERA_DSWX_HLS"
    assert "not a SAR measurement" in scope["measurement_domain"]
    assert any("ground truth" in item for item in scope["not_supported"])


def test_unknown_product_record_type_has_no_inferred_capabilities():
    assert product_scope_for_record_type("ECHO_UNREGISTERED_PRODUCT") is None


def test_product_scope_results_are_copied_before_returning():
    first = product_scope_for_record_type("ECHO_GCOV_PAIR_ANALYSIS")
    first["implemented_paths"].clear()

    second = product_scope_for_record_type("ECHO_GCOV_PAIR_ANALYSIS")
    assert second["implemented_paths"]
