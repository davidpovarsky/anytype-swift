package wallet
const CName = "wallet"
type PublicKey struct { AccountID string }
func (p PublicKey) Account() string { return p.AccountID }
type PrivateKey struct { AccountID string }
func (p PrivateKey) GetPublic() PublicKey { return PublicKey{p.AccountID} }
type Wallet interface { GetAccountPrivkey() PrivateKey; RootPath() string }
type Fixture struct { AccountID, Root string }
func (w *Fixture) GetAccountPrivkey() PrivateKey { return PrivateKey{w.AccountID} }
func (w *Fixture) RootPath() string { return w.Root }
