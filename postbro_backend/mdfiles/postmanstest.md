
AUTH

1 - signup

{
    "email": "melbin50spidey@gmail.com",
    "password": "TestPassword123!",
    "full_name": "Melbin Thomas",
    "company_name": "PostBro"
}

{
    "message": "Account created successfully. Please check your email to verify your account.",
    "user": {
        "id": "de52c7cf-1b51-4be9-beb7-da9e0499e764",
        "email": "melbin50spidey@gmail.com",
        "email_verified": false
    },
    "session": {
        "access_token": null,
        "refresh_token": null
    }
}

Confirm Your Signup
Inbox

Supabase Auth <noreply@mail.app.supabase.io>
4:45 AM (1 minute ago)
to me

Confirm your signup
Follow this link to confirm your user:

Confirm your mail

You're receiving this email because you signed up for an application powered by Supabase ⚡️
Opt out of these emails

2 - login

{
    "email": "melbin50spidey@gmail.com",
    "password": "TestPassword123!"
}

{
    "message": "Login successful",
    "user": {
        "id": "de52c7cf-1b51-4be9-beb7-da9e0499e764",
        "email": "melbin50spidey@gmail.com",
        "email_verified": true,
        "full_name": "Melbin Thomas",
        "company_name": "PostBro"
    },
    "session": {
        "access_token": "eyJhbGciOiJIUzI1NiIsImtpZCI6InY5Sk9EY0Vxd3lmRWZsWFkiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL25la2VqaWxwdG1uYnpobWdsbXljLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJmNjkyYWFjNy0xZjVkLTQ4NjEtODg5Yy1iNzhjOGRmNDI0YzgiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzYzOTQzNjc1LCJpYXQiOjE3NjM5NDAwNzUsImVtYWlsIjoibWVsYmluNTBzcGlkZXlAZ21haWwuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJjb21wYW55X25hbWUiOiJQb3N0QnJvIiwiZW1haWwiOiJtZWxiaW41MHNwaWRleUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiTWVsYmluIFRob21hcyIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiZjY5MmFhYzctMWY1ZC00ODYxLTg4OWMtYjc4YzhkZjQyNGM4In0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NjM5NDAwNzV9XSwic2Vzc2lvbl9pZCI6IjYwNzcxMTQ5LTlkMzAtNDAxMC1iYzE5LWY0ZDA3MDRiNjEzOCIsImlzX2Fub255bW91cyI6ZmFsc2V9.MU_6yok9b9iNagDpGXszJL9F4N6J0YgBJSuxlv3z8NA",
        "refresh_token": "b5viwirvhpsf",
        "expires_at": 1763943675
    }
}

3 - reset password

{
    "email": "melbin50spidey@gmail.com",
    "redirect_to": "http://localhost:3000/reset-password"
}

{
    "message": "Password reset email sent. Please check your inbox."
}

o me

Reset Password
Follow this link to reset the password for your user:

Reset Password

You're receiving this email because you signed up for an application powered by Supabase ⚡️
Opt out of these emails

http://localhost:3000/reset-password#access_token=eyJhbGciOiJIUzI1NiIsImtpZCI6InY5Sk9EY0Vxd3lmRWZsWFkiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2...a24JiNDz2e3la3XyhAJaOwIEc&expires_at=1763943951&expires_in=3600&refresh_token=5jeet5tot5ko&token_type=bearer&type=recovery

NOTES - no check for email formating - accidentaly put email as  .com.com and it worked without error

4 - logout 

{
    "email": "melbin50spidey@gmail.com",
    "password": "TestPassword123!"
}

{
    "message": "Logged out successfully"
}


3 - PROFILE 

1 - update profile

{
    "full_name": "Melbin Inncoent Thomas",
    "company_name": "PostBro LLC"
}

{
    "id": "de52c7cf-1b51-4be9-beb7-da9e0499e764",
    "email": "melbin50spidey@gmail.com",
    "full_name": "Melbin Inncoent Thomas",
    "company_name": "PostBro LLC",
    "profile_image": null,
    "created_at": "2025-11-23T23:15:13.697170Z",
    "updated_at": "2025-11-23T23:33:18.124792Z"
}

2 - get profile

{
    "id": "de52c7cf-1b51-4be9-beb7-da9e0499e764",
    "email": "melbin50spidey@gmail.com",
    "full_name": "Melbin Inncoent Thomas",
    "company_name": "PostBro LLC",
    "profile_image": null,
    "created_at": "2025-11-23T23:15:13.697170Z",
    "updated_at": "2025-11-23T23:33:18.124792Z"
}

4 - plans and subscriptions 

1 - all plans - public

{
    "plans": [
        {
            "id": "946d60bc-d0cb-48be-8478-4d7679adcc76",
            "name": "Free",
            "description": "Perfect for trying out PostBro",
            "price": "0.00",
            "max_handles": 1,
            "max_urls": 5,
            "max_analyses_per_day": 10,
            "is_active": true,
            "created_at": "2025-11-23T22:56:03.993963Z"
        },
        {
            "id": "b49552ce-6ede-49a6-8f64-14ad5bbea858",
            "name": "Basic",
            "description": "Great for small businesses and individuals",
            "price": "10.00",
            "max_handles": 5,
            "max_urls": 20,
            "max_analyses_per_day": 50,
            "is_active": true,
            "created_at": "2025-11-23T22:56:04.222406Z"
        },
        {
            "id": "d422ddb3-59e7-4892-8ea7-a81dae2db0a4",
            "name": "Pro",
            "description": "Advanced features for growing businesses",
            "price": "25.00",
            "max_handles": 20,
            "max_urls": 100,
            "max_analyses_per_day": 500,
            "is_active": true,
            "created_at": "2025-11-23T22:56:04.336713Z"
        }
    ]
}

2 - get current subsription

{
    "id": "3a1f64c9-7b76-490c-8beb-2b4360d53043",
    "plan": {
        "id": "946d60bc-d0cb-48be-8478-4d7679adcc76",
        "name": "Free",
        "description": "Perfect for trying out PostBro",
        "price": "0.00",
        "max_handles": 1,
        "max_urls": 5,
        "max_analyses_per_day": 10,
        "is_active": true,
        "created_at": "2025-11-23T22:56:03.993963Z"
    },
    "status": "active",
    "start_date": "2025-11-23T23:15:14.162708Z",
    "end_date": null,
    "created_at": "2025-11-23T23:15:14.286026Z",
    "updated_at": "2025-11-23T23:15:14.286036Z"
}

3 - subscribe to plan  ( notfully functional cus of stripe not setup yet)

{
    "plan_id": "946d60bc-d0cb-48be-8478-4d7679adcc76"
}

{
    "error": "Invalid input",
    "details": {
        "plan_id": [
            "Free plan cannot be subscribed to directly."
        ]
    }
}


{
    "plan_id": "d422ddb3-59e7-4892-8ea7-a81dae2db0a4"
}

{
    "error": "Stripe integration not yet implemented",
    "message": "Payment processing will be implemented soon",
    "subscription_id": "1ab5b5b6-93ed-4675-b9aa-4ae31f3472ee",
    "plan": "Pro"
}


{
    "plan_id": "d422ddb3-59e7-4892-8ea7-a81dae2db0a4"
}

{
    "error": "You are already subscribed to this plan"
}

4 - upgrade plan

{
    "plan_id": "d422ddb3-59e7-4892-8ea7-a81dae2db0a4"
}

{
    "message": "Successfully upgraded to Pro plan",
    "subscription": {
        "id": "9ce44c41-70e7-4199-a817-cec4f20ed8ed",
        "plan": {
            "id": "d422ddb3-59e7-4892-8ea7-a81dae2db0a4",
            "name": "Pro",
            "description": "Advanced features for growing businesses",
            "price": "25.00",
            "max_handles": 20,
            "max_urls": 100,
            "max_analyses_per_day": 500,
            "is_active": true,
            "created_at": "2025-11-23T22:56:04.336713Z"
        },
        "status": "active",
        "start_date": "2025-11-23T23:39:44.251754Z",
        "end_date": null,
        "created_at": "2025-11-23T23:39:44.252363Z",
        "updated_at": "2025-11-23T23:39:44.252369Z"
    }
}

5 - cancel subscription

{
    "message": "Subscription cancelled successfully",
    "subscription": {
        "id": "9ce44c41-70e7-4199-a817-cec4f20ed8ed",
        "plan": {
            "id": "d422ddb3-59e7-4892-8ea7-a81dae2db0a4",
            "name": "Pro",
            "description": "Advanced features for growing businesses",
            "price": "25.00",
            "max_handles": 20,
            "max_urls": 100,
            "max_analyses_per_day": 500,
            "is_active": true,
            "created_at": "2025-11-23T22:56:04.336713Z"
        },
        "status": "cancelled",
        "start_date": "2025-11-23T23:39:44.251754Z",
        "end_date": "2025-11-23T23:40:35.572363Z",
        "created_at": "2025-11-23T23:39:44.252363Z",
        "updated_at": "2025-11-23T23:40:35.572599Z"
    }
}

6 - subscription history

{
    "subscriptions": [
        {
            "id": "ae001c80-fb95-4a3f-9932-775cbf850290",
            "plan": {
                "id": "946d60bc-d0cb-48be-8478-4d7679adcc76",
                "name": "Free",
                "description": "Perfect for trying out PostBro",
                "price": "0.00",
                "max_handles": 1,
                "max_urls": 5,
                "max_analyses_per_day": 10,
                "is_active": true,
                "created_at": "2025-11-23T22:56:03.993963Z"
            },
            "status": "active",
            "start_date": "2025-11-23T23:40:35.808090Z",
            "end_date": null,
            "created_at": "2025-11-23T23:40:35.808638Z",
            "updated_at": "2025-11-23T23:40:35.808645Z"
        },
        {
            "id": "9ce44c41-70e7-4199-a817-cec4f20ed8ed",
            "plan": {
                "id": "d422ddb3-59e7-4892-8ea7-a81dae2db0a4",
                "name": "Pro",
                "description": "Advanced features for growing businesses",
                "price": "25.00",
                "max_handles": 20,
                "max_urls": 100,
                "max_analyses_per_day": 500,
                "is_active": true,
                "created_at": "2025-11-23T22:56:04.336713Z"
            },
            "status": "cancelled",
            "start_date": "2025-11-23T23:39:44.251754Z",
            "end_date": "2025-11-23T23:40:35.572363Z",
            "created_at": "2025-11-23T23:39:44.252363Z",
            "updated_at": "2025-11-23T23:40:35.572599Z"
        },
        {
            "id": "4d2bf63c-c432-4ee1-8c62-d68d8a5cdea1",
            "plan": {
                "id": "b49552ce-6ede-49a6-8f64-14ad5bbea858",
                "name": "Basic",
                "description": "Great for small businesses and individuals",
                "price": "10.00",
                "max_handles": 5,
                "max_urls": 20,
                "max_analyses_per_day": 50,
                "is_active": true,
                "created_at": "2025-11-23T22:56:04.222406Z"
            },
            "status": "cancelled",
            "start_date": "2025-11-23T23:39:24.852267Z",
            "end_date": "2025-11-23T23:39:44.134307Z",
            "created_at": "2025-11-23T23:39:24.852879Z",
            "updated_at": "2025-11-23T23:39:44.134526Z"
        },
        {
            "id": "1ab5b5b6-93ed-4675-b9aa-4ae31f3472ee",
            "plan": {
                "id": "d422ddb3-59e7-4892-8ea7-a81dae2db0a4",
                "name": "Pro",
                "description": "Advanced features for growing businesses",
                "price": "25.00",
                "max_handles": 20,
                "max_urls": 100,
                "max_analyses_per_day": 500,
                "is_active": true,
                "created_at": "2025-11-23T22:56:04.336713Z"
            },
            "status": "cancelled",
            "start_date": "2025-11-23T23:38:42.018062Z",
            "end_date": "2025-11-23T23:39:24.735730Z",
            "created_at": "2025-11-23T23:38:42.019019Z",
            "updated_at": "2025-11-23T23:39:24.735801Z"
        },
        {
            "id": "5cd0b575-c4aa-4acb-9a8b-4e7a269f2af1",
            "plan": {
                "id": "b49552ce-6ede-49a6-8f64-14ad5bbea858",
                "name": "Basic",
                "description": "Great for small businesses and individuals",
                "price": "10.00",
                "max_handles": 5,
                "max_urls": 20,
                "max_analyses_per_day": 50,
                "is_active": true,
                "created_at": "2025-11-23T22:56:04.222406Z"
            },
            "status": "cancelled",
            "start_date": "2025-11-23T23:36:25.346301Z",
            "end_date": "2025-11-23T23:38:41.900417Z",
            "created_at": "2025-11-23T23:36:25.347705Z",
            "updated_at": "2025-11-23T23:38:41.900716Z"
        },
        {
            "id": "3a1f64c9-7b76-490c-8beb-2b4360d53043",
            "plan": {
                "id": "946d60bc-d0cb-48be-8478-4d7679adcc76",
                "name": "Free",
                "description": "Perfect for trying out PostBro",
                "price": "0.00",
                "max_handles": 1,
                "max_urls": 5,
                "max_analyses_per_day": 10,
                "is_active": true,
                "created_at": "2025-11-23T22:56:03.993963Z"
            },
            "status": "cancelled",
            "start_date": "2025-11-23T23:15:14.162708Z",
            "end_date": "2025-11-23T23:36:25.226220Z",
            "created_at": "2025-11-23T23:15:14.286026Z",
            "updated_at": "2025-11-23T23:36:25.226350Z"
        }
    ],
    "count": 6
}

4 - analysis

1 - analyse post by username

{
    "platform": "x",
    "username": "elonmusk",
    "date_range_type": "last_7_days"
}

{
    "message": "Analysis request created successfully",
    "analysis_request": {
        "id": "9be38d69-dee4-450a-8b53-3a015152e24d",
        "platform": "x",
        "username": "elonmusk",
        "post_urls": [],
        "date_range_type": "last_7_days",
        "start_date": "2025-11-16",
        "end_date": "2025-11-23",
        "status": "processing",
        "task_id": "9443440f-e901-4ae9-b6ff-cfe151440ffc",
        "results": {},
        "error_message": null,
        "created_at": "2025-11-23T23:42:16.926715Z",
        "updated_at": "2025-11-23T23:42:17.447460Z",
        "completed_at": null
    },
    "task_id": "9443440f-e901-4ae9-b6ff-cfe151440ffc",
    "status": "processing",
    "usage_info": {
        "current": 1,
        "limit": 5,
        "remaining": 4
    }
}

2 - analyze posts by url

{
    "platform": "x",
    "post_urls": [
        "https://x.com/elonmusk/status/1812258574049157405"
    ]
}

{
    "message": "Analysis request created successfully",
    "analysis_request": {
        "id": "d4e49960-36d0-4d5f-872b-4183063ee4b2",
        "platform": "x",
        "username": null,
        "post_urls": [
            "https://x.com/elonmusk/status/1812258574049157405"
        ],
        "date_range_type": null,
        "start_date": null,
        "end_date": null,
        "status": "processing",
        "task_id": "f3d98ea3-8bb5-445e-ad29-8750a5120c20",
        "results": {},
        "error_message": null,
        "created_at": "2025-11-23T23:43:28.796738Z",
        "updated_at": "2025-11-23T23:43:29.157879Z",
        "completed_at": null
    },
    "task_id": "f3d98ea3-8bb5-445e-ad29-8750a5120c20",
    "status": "processing",
    "usage_info": {
        "current": 1,
        "limit": 20,
        "remaining": 19
    }
}

3 - analyze posts instagaram

{
    "platform": "instagram",
    "username": "cristiano",
    "date_range_type": "last_30_days"
}

{
    "message": "Analysis request created successfully",
    "analysis_request": {
        "id": "1d446ff0-7731-46b0-834f-d805b6d7e806",
        "platform": "instagram",
        "username": "cristiano",
        "post_urls": [],
        "date_range_type": "last_30_days",
        "start_date": "2025-10-24",
        "end_date": "2025-11-23",
        "status": "processing",
        "task_id": "0e2ab1af-08eb-49a0-8704-b3565571d652",
        "results": {},
        "error_message": null,
        "created_at": "2025-11-23T23:44:25.191068Z",
        "updated_at": "2025-11-23T23:44:25.650809Z",
        "completed_at": null
    },
    "task_id": "0e2ab1af-08eb-49a0-8704-b3565571d652",
    "status": "processing",
    "usage_info": {
        "current": 1,
        "limit": 5,
        "remaining": 4
    }
}

4 - get all analysys reqs

{
    "analysis_requests": [
        {
            "id": "1d446ff0-7731-46b0-834f-d805b6d7e806",
            "platform": "instagram",
            "username": "cristiano",
            "post_urls": [],
            "date_range_type": "last_30_days",
            "start_date": "2025-10-24",
            "end_date": "2025-11-23",
            "status": "processing",
            "task_id": "0e2ab1af-08eb-49a0-8704-b3565571d652",
            "results": {},
            "error_message": null,
            "created_at": "2025-11-23T23:44:25.191068Z",
            "updated_at": "2025-11-23T23:44:25.650809Z",
            "completed_at": null
        },
        {
            "id": "d4e49960-36d0-4d5f-872b-4183063ee4b2",
            "platform": "x",
            "username": null,
            "post_urls": [
                "https://x.com/elonmusk/status/1812258574049157405"
            ],
            "date_range_type": null,
            "start_date": null,
            "end_date": null,
            "status": "processing",
            "task_id": "f3d98ea3-8bb5-445e-ad29-8750a5120c20",
            "results": {},
            "error_message": null,
            "created_at": "2025-11-23T23:43:28.796738Z",
            "updated_at": "2025-11-23T23:43:29.157879Z",
            "completed_at": null
        },
        {
            "id": "9be38d69-dee4-450a-8b53-3a015152e24d",
            "platform": "x",
            "username": "elonmusk",
            "post_urls": [],
            "date_range_type": "last_7_days",
            "start_date": "2025-11-16",
            "end_date": "2025-11-23",
            "status": "processing",
            "task_id": "9443440f-e901-4ae9-b6ff-cfe151440ffc",
            "results": {},
            "error_message": null,
            "created_at": "2025-11-23T23:42:16.926715Z",
            "updated_at": "2025-11-23T23:42:17.447460Z",
            "completed_at": null
        }
    ],
    "count": 3
}

5 - get analysy req by id

{
    "analysis_request": {
        "id": "9be38d69-dee4-450a-8b53-3a015152e24d",
        "platform": "x",
        "username": "elonmusk",
        "post_urls": [],
        "date_range_type": "last_7_days",
        "start_date": "2025-11-16",
        "end_date": "2025-11-23",
        "status": "processing",
        "task_id": "9443440f-e901-4ae9-b6ff-cfe151440ffc",
        "results": {},
        "error_message": null,
        "created_at": "2025-11-23T23:42:16.926715Z",
        "updated_at": "2025-11-23T23:42:17.447460Z",
        "completed_at": null
    }
}

5 - usage

1 - get usage stats

{
    "plan": {
        "id": "b49552ce-6ede-49a6-8f64-14ad5bbea858",
        "name": "Basic",
        "max_handles": 5,
        "max_urls": 20,
        "max_analyses_per_day": 50
    },
    "usage": {
        "platform": "x",
        "date": "2025-11-23",
        "handle_analyses": {
            "used": 1,
            "limit": 5,
            "remaining": 4
        },
        "url_lookups": {
            "used": 1,
            "limit": 20,
            "remaining": 19
        },
        "post_suggestions": {
            "used": 0,
            "limit": 50,
            "remaining": 50
        }
    }
}

2 - get usage limits

{
    "plan": {
        "id": "b49552ce-6ede-49a6-8f64-14ad5bbea858",
        "name": "Basic",
        "description": "Great for small businesses and individuals",
        "price": "10.00",
        "max_handles": 5,
        "max_urls": 20,
        "max_analyses_per_day": 50,
        "is_active": true,
        "created_at": "2025-11-23T22:56:04.222406Z"
    },
    "limits": {
        "max_handles": 5,
        "max_urls": 20,
        "max_analyses_per_day": 50
    }
}

3 - get usage history

{
    "usage_history": [
        {
            "id": "33ca83b5-c0bb-4bb7-bec4-cf8444c3a080",
            "platform": "x",
            "date": "2025-11-23",
            "handle_analyses": 1,
            "url_lookups": 1,
            "post_suggestions": 0,
            "created_at": "2025-11-23T23:42:16.575875Z",
            "updated_at": "2025-11-23T23:43:29.029497Z"
        }
    ],
    "count": 1,
    "start_date": "2025-11-16",
    "end_date": "2025-11-23"
}

