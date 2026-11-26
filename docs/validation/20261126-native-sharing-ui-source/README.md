# Real native owner invitation UI coverage

Source-only addition for the shared permissions screen mounted by the Any engine. The new XCTest creates a real account and workspace using the existing visible onboarding flow, cancels and confirms invitation creation, cancels and confirms revocation, and uses the existing terminate/launch/account/space route after each decision to check persistence. It checks the real alert title and message and unique enabled, hittable controls. It does not read invitation secrets, seed membership, call a fixture API, or synthesize an engine acknowledgement.

The 7,433-byte extension is inserted before the original MiniApps section. Removing that exact range restores every original byte of NativeLaunchTests.swift (f7056f6f...), including the complete MiniApps suffix (cef77342...). Original methods, assertions and deadlines are unchanged. The reviewed new test has a 900-second allowance. Source review by root and native_d_sdk found no blocker.

No XCTest has executed this addition yet. App15 product source remains 379ca3568f247d2fc218ed63df24796d461713c0; the NativeUI runner must declare this later test-source donor explicitly. This test covers the owner's invitation controls and application-process persistence. It does not establish second-member joining, role changes, offline conflict resolution, or full T2 acceptance.
