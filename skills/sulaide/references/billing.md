# Billing: credits, coupons and top-up

All commands use the API key owner's account. The CLI never charges money by itself; payment always happens in the user's own Alipay.

## Check balance first

`sulaide credits --human` → available credits. `sulaide coupons --status available --human` → usable coupons.

## Top up

1. `sulaide packages --human` (same as `sulaide topup packages` or bare `sulaide topup`) lists all active packages from the website catalogue (`id`, `name`, `price`, `original_price`, `credit_amount`, `promotion_label`/`promotion_description`, `purchasable`). Packages with `purchasable: false` cannot be bought from the CLI. Show them to the user and let the user pick. Do not choose a package or amount for them.
2. `sulaide topup --package <ID> --no-wait` creates a pending order and returns JSON with `order_no`, `payable_amount`, `credit_amount` and `payment.pay_url` (an `alipay.com` link, valid until `payment.expires_at`, about 15 minutes). Give the user the link to open in a browser and pay with Alipay (the page shows a QR code for the Alipay app). On a machine where the user is present you may run `sulaide topup --package <ID> --open` instead, which opens the page and waits.
3. Poll with `sulaide topup --status <order_no> --human` (at most every few seconds; stop after the link expires). `status` becomes `paid` and the response includes the new `balance`.

Rules:
- Never enter payment details, never pay for the user, never claim success until `status` is `paid`.
- Re-running `--package` creates a new order; reuse `--status` for an existing order instead. Unpaid orders simply expire.
- Coupons cannot be applied from the CLI. If the user wants to use a coupon, or prefers the website, run `sulaide topup --web` (opens the website recharge page).
- Errors: `TOPUP_TOO_MANY_PENDING_ORDERS` (429) → at most 5 unpaid orders per hour, ask the user to pay an existing one or wait. `PAYMENT_UNAVAILABLE` (503) → online payment is off, use `--web` later. `TOPUP_PACKAGE_NOT_FOUND` → list packages again.
