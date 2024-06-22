# Disable sentry on tests
import sentry_sdk

sentry_sdk.init(dsn='')