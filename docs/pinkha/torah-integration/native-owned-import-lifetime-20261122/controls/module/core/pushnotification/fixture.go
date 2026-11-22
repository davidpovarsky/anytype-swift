package pushnotification
import "context"
const CName = "pushnotification"
type Service interface { RevokeToken(context.Context) error }
