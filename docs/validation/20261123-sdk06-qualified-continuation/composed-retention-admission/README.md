# Composed retained-control admission

This preserves one direct call to verify_retained_controls on the integrated SDK continuation at f6e39500319a0150a0b2a3f1db6ea0fc9b7c7712. It reads and verifies existing evidence; it does not execute any of the tests whose historical receipts it admits.

The call returned 98 retained controller methods, with the 18 separately qualified composition methods and nine separately qualified kernel methods kept in their own fields. All 153 read source/proof inputs were identical before and after. Only sdk06_retained_controls was imported from the repository. No unittest runner, old controller suite, product test or build ran.

The baseline four new admission controls and acceptance's one new composition control retain their own original execution evidence under 20261123-sdk06-retained-controls. Their results are not replaced by this admission receipt.

There is still no actual selector admission. The consumer remains blocked on the real enumeration result and root review/dispatch. The later docs-only correction names the actual build configuration Debug-Anytype and changes none of these 153 inputs.
