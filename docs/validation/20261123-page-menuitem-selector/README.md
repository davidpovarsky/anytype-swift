# Page154 menu item repair
The actual run 45222136118/1 reached the native selection menu after its warning continuation and fresh fixture preparation. Its exact-label query admitted both the MenuItem action and the child StaticText, then correctly refused ambiguity before any menu tap. The complete original artifact and first failure remain retained.

This change restricts that same exact-label query to XCUIElement.ElementType.menuItem. All touch actions, existence/enabled/hittable checks, uniqueness checks, the shared 20-second deadline, one-tap limit, diagnostic attachments and downstream assertions are byte-identical. Only its input plan and profile hash pins are updated.

This is source qualification, not a passing UI acceptance result. No previous pure controls, preparation credit or passed method was replayed. A new UI-only Apple build and the same unresolved mounted journey remain required. The original App remains 68148339c275268795360d71d519a5baf003adf8. SDK06 source at the composition base is unchanged.
