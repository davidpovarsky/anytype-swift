MiniApps return retention - 27 November 2026

Status: source ready; app acceptance pending.
Base: a089ff29a5c0a7e415aac800844505f099a5561d.
The downstream coordinator retains authenticated callbacks until the original account, engine, app home and scene are ready. It preserves native leases, journal, readback and ACK. No pins or upstream files changed.
Eight real Swift tests passed on Oracle Swift6.4.3; 0 failure/skip. See queue-attempt1 original log, XML and result.json, plus verification.json. Coordinator parse and diff checks exited 0.
UIKit typecheck and actual two-app warm/cold return, replay, native file readback and engine/account-switch acceptance remain required in the shared build. No simulator, device or TestFlight success is claimed.
