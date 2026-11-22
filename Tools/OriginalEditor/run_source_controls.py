"""Run the unchanged unittest discovery with an exact reviewed identity/result gate."""
import argparse
import json
from pathlib import Path
import traceback
import unittest

EXPECTED_IDS = (
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_actual_original_two_slices_and_all_signing_page_hashes_parse",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_actual_pinned_upstream_has_only_the_two_required_missing_members",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_actual_post_sign_strict_failure_remains_failure",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_another_package_revision_cannot_get_the_exception",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_changed_architecture_or_unexpected_third_slice_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_changed_native_code_page_hash_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_changed_native_special_hash_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_device_platform_cannot_get_the_simulator_exception",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_different_native_preverification_failure_never_signs",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_entitlement_slot_cannot_replace_the_empty_cms_slot",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_existing_packager_retains_complete_signing_attachments",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_extra_alignment_size_zero_fat_gap_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_missing_original_product_is_refused_before_any_signer",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_native_shape_preserves_exact_residue_and_architecture_pages",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_native_signature_uses_documented_fixed_16k_vm_rounding",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_native_signer_timeout_cannot_produce_qualification",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_nonzero_fat_padding_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_old_x86_four_kib_rounding_is_refused_after_rehashing",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_one_changed_residue_byte_is_refused_on_either_architecture",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_ordinary_resource_or_unknown_payload_is_refused_before_any_signer",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_original_source_change_during_verification_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_other_page_policy_is_refused_even_when_its_page_hashes_match",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_payload_after_the_terminal_fat_allocation_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_pipeline_retains_actual_payloads_and_signs_only_owned_export",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_post_sign_executable_mutation_with_valid_page_hashes_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_post_sign_resource_mutation_is_refused_without_native_credit",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_rehashed_dylib_timestamp_change_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_rehashed_executable_code_change_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_rehashed_linkedit_overlap_with_an_original_segment_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_rehashed_linkedit_symbols_change_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_same_allocation_replacement_preserves_every_nonsignature_byte",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_signature_dataoff_movement_is_not_a_general_padding_exemption",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_signing_identifier_cannot_change",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_slack_must_fit_inside_the_parsed_original_allocation",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_smaller_signature_shrinks_only_to_exact_rounded_allocation",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_symbolic_export_root_is_refused_before_any_signer",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_unaligned_native_signing_allocation_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_unexpected_upstream_signature_success_never_signs",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_unnecessary_virtual_range_growth_is_refused",
    "test_amplitude_simulator_signing.KnownSimulatorSigningControls.test_zeroing_the_nonzero_prior_arm_residue_is_not_an_exemption",
    "test_amplitude_simulator_signing.OriginalSigningDriverFlowControls.test_corrupt_signer_stops_original_driver_before_strict_gate_or_consumer",
    "test_amplitude_simulator_signing.OriginalSigningDriverFlowControls.test_failed_signing_retains_full_after_inventory_without_qualification",
    "test_amplitude_simulator_signing.OriginalSigningDriverFlowControls.test_other_framework_signature_failure_still_blocks_consumer_and_boot",
    "test_amplitude_simulator_signing.OriginalSigningDriverFlowControls.test_whole_driver_keeps_strict_gate_and_exact_transformed_consumer_inputs",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_aliased_export_cannot_sign_original_producer",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_diagnostics_report_all_failures_without_signing_or_qualification",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_different_native_failure_never_authorizes_signing",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_exact_export_preserves_original_bytes_and_keeps_native_strict_gate",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_export_source_byte_difference_fails_before_signing",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_extra_original_resource_is_not_an_authorized_generated_product",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_instruction_and_symbol_bytes_are_preserved_even_with_successful_tool_double",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_native_post_sign_strict_failure_remains_failure",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_native_signer_failure_retains_fail_receipt_and_partial_observation",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_new_entitlements_or_authority_slot_is_rejected",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_non_simulator_product_fails_before_signing",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_signature_movement_and_unreviewed_size_fields_are_rejected",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_signing_cannot_change_original_info_bytes",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_signing_cannot_change_original_producer",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_unexpected_existing_strict_success_does_not_resign",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_unobserved_payload_cannot_hide_in_signature_slack",
    "test_anycrypto_simulator_signing.AnyCryptoExportSigningControls.test_wrong_package_revision_cannot_reach_signer",
    "test_anycrypto_simulator_signing.AnyCryptoOriginalDriverControls.test_failed_signer_preserves_observation_and_blocks_all_later_gates",
    "test_anycrypto_simulator_signing.AnyCryptoOriginalDriverControls.test_original_driver_requires_strict_signature_before_binary_consumer",
    "test_anycrypto_simulator_signing.AnyCryptoOriginalDriverControls.test_unrelated_distribution_mutation_stops_consumer",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_absent_or_unbuilt_work_cannot_create_retained_acceptance",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_all_nineteen_maps_and_six_original_bytes_export_without_producer_paths",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_changed_tracked_header_and_untracked_ignored_header_are_refused",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_committed_alias_escape_and_cycle_are_refused",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_duplicate_missing_and_foreign_modulemap_inputs_are_refused",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_existing_export_and_aliased_export_root_cannot_be_overwritten",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_exported_mutation_extra_member_and_alias_are_refused",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_failed_consumer_outputs_are_retained_only_as_unqualified_bytes",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_foreign_header_root_and_generated_header_reference_are_refused",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_generated_relocation_preserves_exact_nonpath_tokens_and_inverse",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_generated_unsupported_quoted_directive_is_refused_with_raw_evidence",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_git_tracked_alias_chain_is_materialized_and_translation_units_are_absent",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_manifest_traversal_and_missing_root_and_tampered_identity_are_refused",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_pin_drift_or_foreign_actual_compiler_identity_is_refused",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_real_consumer_project_uses_only_exported_maps_headers_and_one_swift_source",
    "test_clang_product_closure.OriginalClangDeclarationControls.test_retention_refuses_source_drift_foreign_attempt_or_failed_build_command",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_aliased_graph_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_changed_access_level_or_filter_flags_are_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_changed_log_is_not_build_authority",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_duplicate_emission_or_path_flags_are_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_duplicate_target_compiler_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_failed_timed_out_foreign_or_changed_timeout_receipt_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_foreign_target_derivedsources_or_module_output_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_full_public_spi_and_extension_bytes_are_retained_without_filtering",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_missing_emit_or_spi_flag_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_missing_empty_or_wrong_main_graph_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_original_debug_and_heart_definitions_are_required",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_preexisting_collection_is_rejected_without_overwrite",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_source_change_rejects_collection",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_source_retirement_during_collection_prevents_success_receipt",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_stale_graph_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_unexpected_graph_directory_member_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_wrong_actual_module_target_sdk_swift_or_working_directory_is_rejected",
    "test_compiler_symbolgraphs.CompilerSymbolGraphCollectionControls.test_wrong_build_scheme_configuration_or_derived_is_rejected",
    "test_framework.ActualTargetPublicSurfaceControls.test_graph_for_another_module_cannot_qualify_the_inspection_facade",
    "test_framework.ActualTargetPublicSurfaceControls.test_imported_dependency_symbols_do_not_become_our_public_editor_api",
    "test_framework.ActualTargetPublicSurfaceControls.test_original_public_editor_constructor_is_rejected",
    "test_framework.BoundedCommandEvidence.test_actual_nonzero_exit_is_preserved_and_cannot_be_pass",
    "test_framework.BoundedCommandEvidence.test_real_timeout_preserves_partial_stdout_and_nonpassing_receipt",
    "test_framework.ObservedOriginalBuildBudget.test_new_route_budget_contains_actual_original_build_and_consumer",
    "test_framework.OriginalProjectPreservation.test_any_additional_original_source_exclusion_is_rejected",
    "test_framework.OriginalProjectPreservation.test_changed_original_app_target_is_rejected_beyond_candidate_hash",
    "test_framework.OriginalProjectPreservation.test_changed_original_compilation_setting_is_rejected",
    "test_framework.OriginalProjectPreservation.test_entrypoint_exception_cannot_target_the_original_app",
    "test_framework.OriginalProjectPreservation.test_framework_cannot_be_an_application_product",
    "test_framework.OriginalProjectPreservation.test_framework_cannot_depend_on_the_original_app_or_test_binary",
    "test_framework.OriginalProjectPreservation.test_framework_has_no_original_app_boot_scripts_or_extensions",
    "test_framework.OriginalProjectPreservation.test_genuine_additive_target_preserves_all_original_app_objects",
    "test_framework.OriginalProjectPreservation.test_new_target_cannot_replace_real_source_groups",
    "test_framework.OriginalProjectPreservation.test_new_target_cannot_substitute_the_original_package_product",
    "test_framework.OriginalProjectPreservation.test_original_baseline_snapshot_is_bound_to_its_git_blob",
    "test_framework.OriginalProjectPreservation.test_original_heart_installer_changes_only_one_new_branch_choice",
    "test_framework.OriginalProjectPreservation.test_original_project_does_not_already_claim_the_new_framework",
    "test_framework.RealFilesystemExportControls.test_app_binary_is_never_accepted_as_framework_input",
    "test_framework.RealFilesystemExportControls.test_duplicate_framework_product_name_fails_closed",
    "test_framework.RealFilesystemExportControls.test_export_preserves_every_real_fixture_byte_without_runtime_credit",
    "test_framework.RealFilesystemExportControls.test_export_refuses_to_overwrite_prior_product",
    "test_framework.RealFilesystemExportControls.test_external_consumer_compiles_only_its_own_importer",
    "test_framework.RealFilesystemExportControls.test_external_resource_symlink_is_rejected",
    "test_framework.RealFilesystemExportControls.test_internal_resource_alias_is_materialized_and_does_not_escape",
    "test_framework.RealFilesystemExportControls.test_missing_original_asset_catalog_is_rejected",
    "test_framework.RealFilesystemExportControls.test_missing_original_font_bundle_is_rejected",
    "test_framework.RealFilesystemExportControls.test_missing_original_hebrew_bundle_is_rejected",
    "test_framework.RealFilesystemExportControls.test_resources_inside_genuine_framework_are_preserved",
    "test_framework.RealFilesystemExportControls.test_test_binary_is_never_accepted_as_framework_input",
    "test_framework.RuntimeReceiptBoundary.test_changed_font_bytes_cannot_pass",
    "test_framework.RuntimeReceiptBoundary.test_expected_language_must_be_actual_process_language",
    "test_framework.RuntimeReceiptBoundary.test_framework_loaded_from_producer_is_not_external_qualification",
    "test_framework.RuntimeReceiptBoundary.test_hebrew_generated_accessor_cannot_pass_with_english_fallback",
    "test_framework.RuntimeReceiptBoundary.test_main_bundle_prefix_is_not_path_ownership",
    "test_framework.RuntimeReceiptBoundary.test_missing_actual_image_cannot_pass",
    "test_framework.RuntimeReceiptBoundary.test_nonfinite_image_geometry_is_rejected",
    "test_framework.RuntimeReceiptBoundary.test_producer_font_fallback_is_rejected_even_with_matching_bytes",
    "test_framework.RuntimeReceiptBoundary.test_stale_nonce_cannot_borrow_a_previous_language_result",
    "test_framework.RuntimeReceiptBoundary.test_swapped_adaptive_color_appearances_cannot_pass",
    "test_framework.RuntimeReceiptBoundary.test_unknown_error_or_partial_runtime_json_cannot_pass",
    "test_framework.RuntimeReceiptBoundary.test_well_formed_synthetic_boundary_is_explicitly_zero_editor_ui",
    "test_framework.RuntimeReceiptBoundary.test_wrong_original_type_or_module_cannot_pass",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_attribute_changed_between_probe_and_read_fails",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_duplicate_name_fails",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_genuine_empty_list_is_empty_without_skipping_the_api",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_list_changed_between_probe_and_read_fails",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_missing_nul_terminator_fails",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_nofollow_inspects_link_attributes",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_oversized_list_fails_before_allocation",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_typed_abi_reads_binary_and_empty_attributes",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_unreadable_attribute_fails",
    "test_framework_duplicates.DarwinAttributeBoundaryControls.test_darwin_unreadable_list_fails_closed",
    "test_framework_duplicates.KnownLibDuplicateControls.test_additional_empty_directory_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_broken_alias_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_changed_materialized_output_cannot_publish_success",
    "test_framework_duplicates.KnownLibDuplicateControls.test_cyclic_internal_directory_alias_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_different_binary_byte_fails_without_choosing_the_first",
    "test_framework_duplicates.KnownLibDuplicateControls.test_different_directory_mode_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_different_extended_attribute_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_different_file_mode_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_different_literal_symlink_target_fails_even_with_same_resolved_bytes",
    "test_framework_duplicates.KnownLibDuplicateControls.test_different_relative_filename_with_same_bytes_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_different_signature_byte_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_duplicate_original_editor_framework_still_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_equal_internal_file_alias_is_materialized",
    "test_framework_duplicates.KnownLibDuplicateControls.test_equal_versioned_directory_aliases_preserve_all_resolved_members",
    "test_framework_duplicates.KnownLibDuplicateControls.test_exact_known_pair_preserves_complete_equal_inputs_and_exports_one_lib",
    "test_framework_duplicates.KnownLibDuplicateControls.test_known_input_changed_during_copy_cannot_publish_success",
    "test_framework_duplicates.KnownLibDuplicateControls.test_missing_original_editor_framework_still_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_missing_resource_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_only_timestamps_may_differ",
    "test_framework_duplicates.KnownLibDuplicateControls.test_product_alias_to_owned_but_other_framework_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_root_framework_alias_is_not_an_independent_known_product",
    "test_framework_duplicates.KnownLibDuplicateControls.test_same_pair_under_unreviewed_parent_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_special_fifo_fails_without_reading_it",
    "test_framework_duplicates.KnownLibDuplicateControls.test_unexpected_third_lib_location_fails",
    "test_framework_duplicates.KnownLibDuplicateControls.test_whole_exporter_darwin_path_does_not_require_linux_os_xattr",
    "test_framework_flow.OriginalDriverFlowControls.test_boot_command_failure_keeps_build_evidence_but_never_runs_bootstatus_or_install",
    "test_framework_flow.OriginalDriverFlowControls.test_build_graph_consumer_and_signature_complete_before_original_boot_pair",
    "test_framework_flow.OriginalDriverFlowControls.test_consumer_compile_failure_cannot_boot_or_install",
    "test_framework_flow.OriginalDriverFlowControls.test_different_embedded_product_cannot_reach_boot_or_install",
    "test_framework_flow.OriginalDriverFlowControls.test_multiple_notices_preserve_exact_contents_and_consumer_destination",
    "test_framework_flow.OriginalDriverFlowControls.test_one_notice_preserves_selected_simulator_for_both_original_build_commands",
    "test_framework_flow.OriginalDriverFlowControls.test_original_framework_compile_failure_cannot_boot_or_install",
    "test_framework_flow.OriginalDriverFlowControls.test_original_public_surface_tool_failure_cannot_boot_or_install",
    "test_framework_flow.OriginalDriverFlowControls.test_original_source_only_admission_never_invokes_any_tool_or_work_directory",
    "test_framework_flow.OriginalDriverFlowControls.test_same_180_second_boot_timeout_retains_partial_builds_without_runtime_credit",
    "test_framework_source_retention.OriginalRawCompilerEvidenceControls.test_duplicate_generated_bundle_accessor_still_fails",
    "test_framework_source_retention.OriginalRawCompilerEvidenceControls.test_foreign_unowned_source_still_fails",
    "test_framework_source_retention.OriginalRawCompilerEvidenceControls.test_malformed_original_source_line_still_fails",
    "test_framework_source_retention.OriginalRawCompilerEvidenceControls.test_missing_generated_bundle_accessor_still_fails",
    "test_framework_source_retention.OriginalRawCompilerEvidenceControls.test_missing_original_input_still_fails",
    "test_framework_source_retention.OriginalRawCompilerEvidenceControls.test_original_app_entrypoint_still_fails",
    "test_framework_source_retention.OriginalRawCompilerEvidenceControls.test_original_packager_retains_all_four_exact_raw_proofs_as_text",
    "test_framework_temporary_paths.TemporaryRootAliasControls.test_known_input_mutation_is_really_injected_and_refused_under_directory_alias",
    "test_framework_temporary_paths.TemporaryRootAliasControls.test_materialized_mutation_is_really_injected_and_refused_under_directory_alias",
    "test_framework_temporary_paths.TemporaryRootAliasControls.test_original_driver_import_context_reaches_consumer_under_directory_alias",
    "test_framework_temporary_paths.TemporaryRootAliasControls.test_original_raw_compiler_proofs_are_retained_under_directory_alias",
    "test_host_framework_contract.HostFrameworkContractControls.test_all_reviewed_public_and_spi_paths_are_required_without_ui_credit",
    "test_host_framework_contract.HostFrameworkContractControls.test_different_shared_package_pin_rejected_even_with_updated_project_hash",
    "test_host_framework_contract.HostFrameworkContractControls.test_malformed_spi_marker_does_not_grant_qualification_scope",
    "test_host_framework_contract.HostFrameworkContractControls.test_missing_real_capture_entrypoint_rejects_inspection_only_surface",
    "test_host_framework_contract.HostFrameworkContractControls.test_public_raw_runtime_helper_is_not_the_qualified_spi",
    "test_host_framework_contract.HostFrameworkContractControls.test_public_unowned_host_constructor_is_rejected",
    "test_host_framework_contract.HostFrameworkContractControls.test_qualification_declarations_require_actual_spi_scope",
    "test_host_framework_contract.HostFrameworkContractControls.test_regular_host_declarations_cannot_be_hidden_as_spi",
    "test_host_framework_contract.HostFrameworkContractControls.test_same_spelling_from_a_foreign_source_is_not_a_host_capability",
    "test_host_framework_contract.HostFrameworkContractControls.test_symbol_graph_emission_cannot_spill_into_original_application",
    "test_observed_package_simulator_signing.DependencyCheckoutSourceClosureControls.test_unchanged_source_accepts_separate_owned_generated_build_metadata",
    "test_observed_package_simulator_signing.DependencyCheckoutSourceClosureControls.test_untracked_swift_resource_and_ignored_source_are_rejected_without_cleanup",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_alias_cannot_redirect_signing_to_original_producer",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_device_product_is_not_an_eligible_simulator_export",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_different_native_failure_is_not_a_signing_exception",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_dirty_local_module_bytes_fail_against_pinned_blob",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_every_exact_profile_preserves_all_original_and_nested_bytes",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_export_must_match_original_before_native_signing",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_extra_local_module_file_is_not_in_the_source_closure",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_modified_executable_instruction_stops_acceptance",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_modified_original_producer_stops_acceptance",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_native_post_sign_failure_preserves_receipt_without_qualification",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_nested_resource_metadata_mutation_is_rejected",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_nested_signature_must_verify_before_any_root_signing",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_resource_and_nested_signature_mutations_are_rejected",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_unexpected_valid_original_is_not_resigned",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_unknown_resource_or_signature_member_is_refused",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_unreviewed_product_name_has_no_wildcard_exception",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_wrong_external_revision_never_reaches_native_signer",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_wrong_local_module_tree_never_reaches_native_signer",
    "test_observed_package_simulator_signing.ObservedExportSigningControls.test_wrong_new_signing_identifier_is_rejected",
    "test_observed_package_simulator_signing.ObservedPackageOriginalDriverControls.test_failed_signer_keeps_failure_inventory_and_stops_native_acceptance",
    "test_observed_package_simulator_signing.ObservedPackageOriginalDriverControls.test_original_driver_keeps_full_strict_gate_before_external_consumer",
    "test_observed_package_simulator_signing.ObservedPackageOriginalDriverControls.test_unrelated_distribution_change_cannot_reach_consumer",
    "test_symbolgraph_import_context.ActualCompilerImportContextControls.test_ambiguous_original_target_command_is_rejected",
    "test_symbolgraph_import_context.ActualCompilerImportContextControls.test_changed_log_is_rejected_before_any_extraction_authority",
    "test_symbolgraph_import_context.ActualCompilerImportContextControls.test_failed_timed_out_or_foreign_build_is_not_import_authority",
    "test_symbolgraph_import_context.ActualCompilerImportContextControls.test_observed_original_context_keeps_all_clang_imports_and_implicit_cache",
    "test_symbolgraph_import_context.ActualCompilerImportContextControls.test_wrong_target_sdk_language_or_cache_is_rejected",
)
EXPECTED_COUNT = 237


def cases(suite):
    if isinstance(suite, unittest.TestSuite):
        for child in suite:
            yield from cases(child)
    elif isinstance(suite, unittest.TestCase):
        yield suite
    else:
        raise RuntimeError('Unexpected unittest discovery object')


class ObservedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_ids = []
        self.passed_ids = []

    def startTest(self, test):
        self.started_ids.append(test.id())
        super().startTest(test)

    def addSuccess(self, test):
        self.passed_ids.append(test.id())
        super().addSuccess(test)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 1, 'status': 'FAIL', 'phase': 'DISCOVERY',
               'expected_count': EXPECTED_COUNT, 'expected_ids': list(EXPECTED_IDS),
               'scope': 'Python source controls only; no Apple build or consumer qualification'}
    code = 1
    try:
        suite = unittest.defaultTestLoader.discover(
            start_dir=str(Path(__file__).resolve().parent), pattern='test_*.py')
        actual_ids = sorted(test.id() for test in cases(suite))
        receipt['discovered_ids'] = actual_ids
        if (len(EXPECTED_IDS) != EXPECTED_COUNT or len(set(EXPECTED_IDS)) != EXPECTED_COUNT
                or actual_ids != list(EXPECTED_IDS)):
            raise RuntimeError(f'Actual unittest discovery differs from the exact reviewed {EXPECTED_COUNT} cases')
        receipt['phase'] = 'EXECUTION'
        result = unittest.TextTestRunner(verbosity=2, resultclass=ObservedResult).run(suite)
        receipt.update({
            'tests_run': result.testsRun,
            'started_ids': result.started_ids,
            'passed_ids': result.passed_ids,
            'failures': [{'id': test.id(), 'traceback': trace} for test, trace in result.failures],
            'errors': [{'id': test.id(), 'traceback': trace} for test, trace in result.errors],
            'skipped': [{'id': test.id(), 'reason': reason} for test, reason in result.skipped],
            'expected_failures': [{'id': test.id(), 'traceback': trace}
                                  for test, trace in result.expectedFailures],
            'unexpected_successes': [test.id() for test in result.unexpectedSuccesses],
        })
        if (result.testsRun != EXPECTED_COUNT
                or sorted(result.started_ids) != list(EXPECTED_IDS)
                or sorted(result.passed_ids) != list(EXPECTED_IDS)
                or result.failures or result.errors or result.skipped
                or result.expectedFailures or result.unexpectedSuccesses
                or not result.wasSuccessful()):
            raise RuntimeError(f'The exact {EXPECTED_COUNT} source controls did not all pass without skips')
        receipt['status'] = f'PASS_SOURCE_CONTROLS_{EXPECTED_COUNT}'
        receipt['phase'] = 'COMPLETE'
        code = 0
    except BaseException as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
        traceback.print_exc()
    finally:
        (args.evidence / 'source-controls-result.json').write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
