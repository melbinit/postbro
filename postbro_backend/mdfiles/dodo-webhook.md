When payment was success - got 3 hits to test webhook.

1 -----

Request
Response
Details
URL	
/api/v1/in/e_CHgYFUwEbiIui5GQQleesxMXuuf/
Method	
POST
Date	
December 5, 2025 at 4:29 PM
IP	
52.24.126.164
Response Code	
204
Request Headers
accept	
*/*
content-length	
1337
content-type	
application/json
user-agent	
Svix-Webhooks/1.81.0 (sender-9YMgn; +https://www.svix.com/http-sender/)
webhook-id	
msg_36QISrXF7LSzxbkSFqLvifAzaUJ
webhook-signature	
v1,clxw/rVFeUe9sBmtg4BCyjoKGi7PirdcfHihWwAUYk8=
webhook-timestamp	
1764932370
Request Body

Raw?

{4 items
"business_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"data":{32 items
"billing":{5 items
"city":string"Dubai"
"country":string"AE"
"state":string"Dubai"
"street":string"Dubai"
"zipcode":string"670673"
}
"brand_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"business_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"card_issuing_country":NULL
"card_last_four":string"4242"
"card_network":string"visa"
"card_type":string"credit"
"checkout_session_id":string"cks_SS4Og7wyFoeXGEkAYzLWB"
"created_at":string"2025-12-05T10:58:30.240548Z"
"currency":string"USD"
"customer":{5 items
"customer_id":string"cus_gxLktbgUk5vCdOxxAsyes"
"email":string"imelbinthomas@gmail.com"
"metadata":{}0 items
"name":string"Melbin"
"phone_number":NULL
}
"digital_products_delivered":boolfalse
"discount_id":NULL
"disputes":[]0 items
"error_code":NULL
"error_message":NULL
"metadata":{4 items
"plan_id":string"d422ddb3-59e7-4892-8ea7-a81dae2db0a4"
"plan_name":string"Pro"
"subscription_id":string"dd6dd189-64ec-4d40-b1e0-b43013748dab"
"user_id":string"de52c7cf-1b51-4be9-beb7-da9e0499e764"
}
"payload_type":string"Payment"
"payment_id":string"pay_XqQTQH5M42D5cVMFYIfMs"
"payment_link":string"https://test.checkout.dodopayments.com/x4BKWKxS"
"payment_method":string"card"
"payment_method_type":NULL
"product_cart":NULL
"refunds":[]0 items
"settlement_amount":int6195
"settlement_currency":string"USD"
"settlement_tax":int295
"status":string"succeeded"
"subscription_id":string"sub_wEN3a6fR2hqIuGg8Cbojc"
"tax":int295
"total_amount":int6195
"updated_at":NULL
}
"timestamp":string"2025-12-05T10:59:30.550128Z"
"type":string"payment.succeeded"
}

2 -------

Request
Response
Details
URL	
/api/v1/in/e_CHgYFUwEbiIui5GQQleesxMXuuf/
Method	
POST
Date	
December 5, 2025 at 4:29 PM
IP	
50.112.21.217
Response Code	
204
Request Headers
accept	
*/*
content-length	
1317
content-type	
application/json
user-agent	
Svix-Webhooks/1.81.0 (sender-9YMgn; +https://www.svix.com/http-sender/)
webhook-id	
msg_36QIStWI2eqbGpfLftVj7VUHM3r
webhook-signature	
v1,uqswDAFnE7Ogoz/WFXOr12ur0i9NZqanRvr32M4aV1k=
webhook-timestamp	
1764932371
Request Body

Raw?

{4 items
"business_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"data":{29 items
"addons":[]0 items
"billing":{5 items
"city":string"Dubai"
"country":string"AE"
"state":string"Dubai"
"street":string"Dubai"
"zipcode":string"670673"
}
"cancel_at_next_billing_date":boolfalse
"cancelled_at":NULL
"created_at":string"2025-12-05T10:58:30.240548Z"
"currency":string"USD"
"customer":{5 items
"customer_id":string"cus_gxLktbgUk5vCdOxxAsyes"
"email":string"imelbinthomas@gmail.com"
"metadata":{}0 items
"name":string"Melbin"
"phone_number":NULL
}
"discount_cycles_remaining":NULL
"discount_id":NULL
"expires_at":string"2030-12-05T10:59:30.565625Z"
"metadata":{4 items
"plan_id":string"d422ddb3-59e7-4892-8ea7-a81dae2db0a4"
"plan_name":string"Pro"
"subscription_id":string"dd6dd189-64ec-4d40-b1e0-b43013748dab"
"user_id":string"de52c7cf-1b51-4be9-beb7-da9e0499e764"
}
"meters":[]0 items
"next_billing_date":string"2026-01-05T10:59:30.565625Z"
"on_demand":boolfalse
"payload_type":string"Subscription"
"payment_frequency_count":int1
"payment_frequency_interval":string"Month"
"payment_method_id":string"pm_s8Kfm2o7wmFX1Iljujop"
"previous_billing_date":string"2025-12-05T10:58:30.240548Z"
"product_id":string"pdt_tPnzNw9fAfjZHnCSbyndn"
"quantity":int1
"recurring_pre_tax_amount":int5900
"status":string"active"
"subscription_id":string"sub_wEN3a6fR2hqIuGg8Cbojc"
"subscription_period_count":int5
"subscription_period_interval":string"Year"
"tax_id":NULL
"tax_inclusive":boolfalse
"trial_period_days":int0
}
"timestamp":string"2025-12-05T10:59:30.550128Z"
"type":string"subscription.renewed"
}

3 -------------

Request
Response
Details
URL	
/api/v1/in/e_CHgYFUwEbiIui5GQQleesxMXuuf/
Method	
POST
Date	
December 5, 2025 at 4:29 PM
IP	
44.228.126.217
Response Code	
204
Request Headers
accept	
*/*
content-length	
1316
content-type	
application/json
user-agent	
Svix-Webhooks/1.81.0 (sender-9YMgn; +https://www.svix.com/http-sender/)
webhook-id	
msg_36QISvLb8yWKaVX3vCXtS99d8Xf
webhook-signature	
v1,EnGMrlcjPekwhbRyRxdmtbkIHMrX2plX0lh/rpa4ayg=
webhook-timestamp	
1764932371
Request Body

Raw?

{4 items
"business_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"data":{29 items
"addons":[]0 items
"billing":{5 items
"city":string"Dubai"
"country":string"AE"
"state":string"Dubai"
"street":string"Dubai"
"zipcode":string"670673"
}
"cancel_at_next_billing_date":boolfalse
"cancelled_at":NULL
"created_at":string"2025-12-05T10:58:30.240548Z"
"currency":string"USD"
"customer":{5 items
"customer_id":string"cus_gxLktbgUk5vCdOxxAsyes"
"email":string"imelbinthomas@gmail.com"
"metadata":{}0 items
"name":string"Melbin"
"phone_number":NULL
}
"discount_cycles_remaining":NULL
"discount_id":NULL
"expires_at":string"2030-12-05T10:59:30.565625Z"
"metadata":{4 items
"plan_id":string"d422ddb3-59e7-4892-8ea7-a81dae2db0a4"
"plan_name":string"Pro"
"subscription_id":string"dd6dd189-64ec-4d40-b1e0-b43013748dab"
"user_id":string"de52c7cf-1b51-4be9-beb7-da9e0499e764"
}
"meters":[]0 items
"next_billing_date":string"2026-01-05T10:59:30.565625Z"
"on_demand":boolfalse
"payload_type":string"Subscription"
"payment_frequency_count":int1
"payment_frequency_interval":string"Month"
"payment_method_id":string"pm_s8Kfm2o7wmFX1Iljujop"
"previous_billing_date":string"2025-12-05T10:58:30.240548Z"
"product_id":string"pdt_tPnzNw9fAfjZHnCSbyndn"
"quantity":int1
"recurring_pre_tax_amount":int5900
"status":string"active"
"subscription_id":string"sub_wEN3a6fR2hqIuGg8Cbojc"
"subscription_period_count":int5
"subscription_period_interval":string"Year"
"tax_id":NULL
"tax_inclusive":boolfalse
"trial_period_days":int0
}
"timestamp":string"2025-12-05T10:59:30.550128Z"
"type":string"subscription.active"
}

When payment failed -

1 -----
Request
Response
Details
URL	
/api/v1/in/e_CHgYFUwEbiIui5GQQleesxMXuuf/
Method	
POST
Date	
December 5, 2025 at 4:42 PM
IP	
44.228.126.217
Response Code	
204
Request Headers
accept	
*/*
content-length	
1270
content-type	
application/json
user-agent	
Svix-Webhooks/1.81.0 (sender-9YMgn; +https://www.svix.com/http-sender/)
webhook-id	
msg_36QK2sr3IjjT40jlIPJbKScCCNz
webhook-signature	
v1,mGyUhXEwwZ4E8dQYNuis51kwVUpp6m0PtPzlPaehNbQ=
webhook-timestamp	
1764933150
Request Body

Raw?

{4 items
"business_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"data":{29 items
"addons":[]0 items
"billing":{5 items
"city":string"Dubai"
"country":string"AE"
"state":string"Dubai"
"street":string"Dubai"
"zipcode":string"670673"
}
"cancel_at_next_billing_date":boolfalse
"cancelled_at":NULL
"created_at":string"2025-12-05T11:12:07.372338Z"
"currency":string"USD"
"customer":{5 items
"customer_id":string"cus_gxLktbgUk5vCdOxxAsyes"
"email":string"imelbinthomas@gmail.com"
"metadata":{}0 items
"name":string"Melbin"
"phone_number":NULL
}
"discount_cycles_remaining":NULL
"discount_id":NULL
"expires_at":NULL
"metadata":{4 items
"plan_id":string"d422ddb3-59e7-4892-8ea7-a81dae2db0a4"
"plan_name":string"Pro"
"subscription_id":string"323f6bc6-5a1b-42b6-b35f-ae0a191824a6"
"user_id":string"de52c7cf-1b51-4be9-beb7-da9e0499e764"
}
"meters":[]0 items
"next_billing_date":string"2025-12-05T11:12:07.372338Z"
"on_demand":boolfalse
"payload_type":string"Subscription"
"payment_frequency_count":int1
"payment_frequency_interval":string"Month"
"payment_method_id":NULL
"previous_billing_date":string"2025-12-05T11:12:07.372338Z"
"product_id":string"pdt_tPnzNw9fAfjZHnCSbyndn"
"quantity":int1
"recurring_pre_tax_amount":int5900
"status":string"failed"
"subscription_id":string"sub_kAY91EyScqZPo6Z08sycu"
"subscription_period_count":int5
"subscription_period_interval":string"Year"
"tax_id":NULL
"tax_inclusive":boolfalse
"trial_period_days":int0
}
"timestamp":string"2025-12-05T11:12:29.514624Z"
"type":string"subscription.failed"
}

2 -----

Request
Response
Details
URL	
/api/v1/in/e_CHgYFUwEbiIui5GQQleesxMXuuf/
Method	
POST
Date	
December 5, 2025 at 4:42 PM
IP	
44.228.126.217
Response Code	
204
Request Headers
accept	
*/*
content-length	
1370
content-type	
application/json
user-agent	
Svix-Webhooks/1.81.0 (sender-9YMgn; +https://www.svix.com/http-sender/)
webhook-id	
msg_36QK2ssmENgb3EOmeBpP7LePaCl
webhook-signature	
v1,fxLY/DjMwDCM47Xhz/tnLXdUNk4wJK1HuThlknmZSvs=
webhook-timestamp	
1764933150
Request Body

Raw?

{4 items
"business_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"data":{32 items
"billing":{5 items
"city":string"Dubai"
"country":string"AE"
"state":string"Dubai"
"street":string"Dubai"
"zipcode":string"670673"
}
"brand_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"business_id":string"bus_hnNKp4hJX76Hm17Yez3gr"
"card_issuing_country":NULL
"card_last_four":string"0002"
"card_network":string"visa"
"card_type":string"credit"
"checkout_session_id":string"cks_0Nh2vIbCoN988kqBbVAjQ"
"created_at":string"2025-12-05T11:12:07.372338Z"
"currency":string"AED"
"customer":{5 items
"customer_id":string"cus_gxLktbgUk5vCdOxxAsyes"
"email":string"imelbinthomas@gmail.com"
"metadata":{}0 items
"name":string"Melbin"
"phone_number":NULL
}
"digital_products_delivered":boolfalse
"discount_id":NULL
"disputes":[]0 items
"error_code":string"INSUFFICIENT_FUNDS"
"error_message":string"Your card was declined."
"metadata":{4 items
"plan_id":string"d422ddb3-59e7-4892-8ea7-a81dae2db0a4"
"plan_name":string"Pro"
"subscription_id":string"323f6bc6-5a1b-42b6-b35f-ae0a191824a6"
"user_id":string"de52c7cf-1b51-4be9-beb7-da9e0499e764"
}
"payload_type":string"Payment"
"payment_id":string"pay_nS2Ijtl0NiLe0Nbw9gfln"
"payment_link":string"https://test.checkout.dodopayments.com/YtJxwbzd"
"payment_method":string"card"
"payment_method_type":NULL
"product_cart":NULL
"refunds":[]0 items
"settlement_amount":int6195
"settlement_currency":string"USD"
"settlement_tax":int295
"status":string"failed"
"subscription_id":string"sub_kAY91EyScqZPo6Z08sycu"
"tax":int1127
"total_amount":int23665
"updated_at":NULL
}
"timestamp":string"2025-12-05T11:12:29.514624Z"
"type":string"payment.failed"
}