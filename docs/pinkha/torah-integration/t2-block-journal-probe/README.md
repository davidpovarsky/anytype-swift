# T2 native block-journal state probe

This isolated Go test module exercises the pinned Anytype Heart tag
`v0.50.21-nightly.20260824.1` (commit
`7e8f5535add386ff5f7573cde47e095c867ab724`). It does not patch or replace
Heart.

Run:

```console
go test -mod=readonly -v -count=1 ./...
```

The probe covers only Tier B state/change replay. It is not middleware
persistence and is not a two-client synchronization proof.
