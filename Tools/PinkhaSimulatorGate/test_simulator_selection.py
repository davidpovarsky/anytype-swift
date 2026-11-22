import copy
import unittest

from simulator_selection import choose_pair


PREFIX = "com.apple.CoreSimulator.SimRuntime.iOS-"
TABLET = "com.apple.CoreSimulator.SimDeviceType.iPad-mini-A20-Pro"
OLDER = "com.apple.CoreSimulator.SimDeviceType.iPad-Air-13-inch-M4"
PHONE = "com.apple.CoreSimulator.SimDeviceType.iPhone-19-4"


def device(identifier=TABLET, family="iPad", minimum=27*65536+2*256):
    return dict(identifier=identifier, name=identifier.rsplit(".", 1)[-1], productFamily=family,
                minRuntimeVersion=minimum, maxRuntimeVersion=0xFFFFFFFF)


def runtime(identifier="27-2", version="27.2", supported=(TABLET, OLDER)):
    return dict(identifier=PREFIX+identifier, version=version, isAvailable=True, buildversion="original-build",
                supportedArchitectures=["arm64"], supportedDeviceTypes=[
                    dict(identifier=value, productFamily="iPhone" if value == PHONE else "iPad") for value in supported])


class SimulatorSelectionTests(unittest.TestCase):
    def inventories(self):
        return (dict(runtimes=[runtime(), runtime("27-2-iPhone19-4", supported=(PHONE,))]),
                dict(devicetypes=[device(), device(OLDER, minimum=17*65536), device(PHONE, "iPhone")]))

    def test_model_specific_phone_runtime_cannot_win_an_ipad_selection(self):
        runtimes, devices = self.inventories()
        value = choose_pair(runtimes, devices)
        self.assertEqual(value["runtime"]["identifier"], PREFIX+"27-2")
        self.assertEqual(value["device"]["identifier"], TABLET)
        phone = choose_pair(runtimes, devices, product_family="iPhone")
        self.assertEqual(phone["runtime"]["identifier"], PREFIX+"27-2-iPhone19-4")

    def test_compatible_older_runtime_survives_newer_phone_only_runtime(self):
        _, devices = self.inventories()
        runtimes = dict(runtimes=[runtime("27-0", "27.0", (OLDER,)), runtime("27-2-iPhone19-4", supported=(PHONE,))])
        self.assertEqual(choose_pair(runtimes, devices)["runtime"]["version"], "27.0")

    def test_actual_minor_and_patch_version_are_checked_against_type_bounds(self):
        runtimes, devices = self.inventories()
        devices["devicetypes"][0]["minRuntimeVersion"] = 27*65536+2*256+1
        self.assertEqual(choose_pair(runtimes, devices)["device"]["identifier"], OLDER)
        runtimes["runtimes"][0]["version"] = "27.2.1"
        self.assertEqual(choose_pair(runtimes, devices)["device"]["identifier"], TABLET)

    def test_unavailable_architecture_and_missing_matrix_never_guess_compatibility(self):
        runtimes, devices = self.inventories()
        for field, replacement in [("isAvailable", False), ("supportedArchitectures", ["x86_64"]),
                                   ("supportedDeviceTypes", [])]:
            altered = copy.deepcopy(runtimes); altered["runtimes"][0][field] = replacement
            with self.assertRaisesRegex(ValueError, "No explicitly compatible"):
                choose_pair(altered, devices)
        altered = copy.deepcopy(runtimes); altered["runtimes"][0].pop("supportedDeviceTypes")
        with self.assertRaisesRegex(ValueError, "Missing simulator"):
            choose_pair(altered, devices)

    def test_duplicate_malformed_and_uninstalled_types_are_rejected_or_excluded(self):
        runtimes, devices = self.inventories()
        duplicated = copy.deepcopy(runtimes); duplicated["runtimes"].append(duplicated["runtimes"][0])
        with self.assertRaisesRegex(ValueError, "repeated"):
            choose_pair(duplicated, devices)
        devices["devicetypes"][0]["minRuntimeVersion"] = True
        with self.assertRaisesRegex(ValueError, "Malformed"):
            choose_pair(runtimes, devices)
        devices["devicetypes"] = [device(PHONE, "iPhone")]
        with self.assertRaisesRegex(ValueError, "No explicitly compatible"):
            choose_pair(runtimes, devices)


if __name__ == "__main__":
    unittest.main()
