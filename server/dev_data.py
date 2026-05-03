from uuid import UUID


TENANT_1 = UUID("550e8400-e29b-41d4-a716-446655440000")
TENANT_2 = UUID("11111111-1111-1111-1111-111111111111")
TENANT_3 = UUID("22222222-2222-2222-2222-222222222222")

FAKE_USERS = [
    {
        "username": "admin",
        "email": "admin@teladoc.com",
        "password": "password123",
        "role": "admin",
        "display_name": "Admin User",
        "tenant_id": None,
    },
    {
        "username": "tenant1",
        "email": "tenant1@teladoc.com",
        "password": "password123",
        "role": "tenant",
        "display_name": "Tenant 1 User",
        "tenant_id": str(TENANT_1),
    },
    {
        "username": "tenant2",
        "email": "tenant2@teladoc.com",
        "password": "password123",
        "role": "tenant",
        "display_name": "Tenant 2 User",
        "tenant_id": str(TENANT_2),
    },
    {
        "username": "tenant3",
        "email": "tenant3@teladoc.com",
        "password": "password123",
        "role": "tenant",
        "display_name": "Tenant 3 User",
        "tenant_id": str(TENANT_3),
    },
]
