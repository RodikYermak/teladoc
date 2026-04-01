import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import TokenCard from '../components/TokenCard';
import EventForm from '../components/EventForm';
import UsageByDayTable from '../components/UsageByDayTable';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

function buildAuthHeaders(auth) {
    if (!auth?.token) return {};
    return {
        Authorization: `Bearer ${auth.token}`,
    };
}

export default function Dashboard({ auth, onUnauthorized }) {
    const [events, setEvents] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [tenantSummary, setTenantSummary] = useState(null);
    const [selectedAdminTenantId, setSelectedAdminTenantId] = useState('');
    const [loading, setLoading] = useState(true);

    const isAdmin = auth?.user?.role === 'admin';
    const tenantScopedId = auth?.user?.tenant_id || null;

    const fetchDashboardData = useCallback(async () => {
        try {
            const headers = buildAuthHeaders(auth);

            const [eventsResponse, tenantsResponse] = await Promise.all([
                api.get('/v1/usage/events', { headers }),
                api.get('/v1/tenants', { headers }),
            ]);

            const fetchedEvents = eventsResponse.data.events || [];
            const fetchedTenants = tenantsResponse.data.tenants || [];

            setEvents(fetchedEvents);
            setTenants(fetchedTenants);

            if (isAdmin) {
                const selectedTenant =
                    fetchedTenants.find((tenant) => tenant.tenant_id === selectedAdminTenantId) ||
                    fetchedTenants[0] ||
                    null;

                setTenantSummary(selectedTenant);
                setSelectedAdminTenantId(selectedTenant?.tenant_id || '');
            } else {
                const myTenant =
                    fetchedTenants.find((tenant) => tenant.tenant_id === tenantScopedId) || null;
                setTenantSummary(myTenant);
            }
        } catch (error) {
            if (error.response?.status === 401) {
                onUnauthorized();
            }
            console.error('Error fetching dashboard data:', error);
        } finally {
            setLoading(false);
        }
    }, [auth, isAdmin, onUnauthorized, selectedAdminTenantId, tenantScopedId]);

    useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    useEffect(() => {
        if (!isAdmin) return;

        const selectedTenant =
            tenants.find((tenant) => tenant.tenant_id === selectedAdminTenantId) || null;

        setTenantSummary(selectedTenant);
    }, [isAdmin, tenants, selectedAdminTenantId]);

    const handleCreateEvent = async (payload, allowOverage) => {
        try {
            const response = await api.post(
                `/v1/usage/events${allowOverage ? '?allow_overage=true' : ''}`,
                payload,
                {
                    headers: buildAuthHeaders(auth),
                },
            );

            if (!response.data.idempotency_replayed) {
                setEvents((prev) => [response.data, ...prev]);

                setTenants((prevTenants) =>
                    prevTenants.map((tenant) =>
                        tenant.tenant_id === response.data.tenant_id
                            ? {
                                  ...tenant,
                                  month_to_date_usage:
                                      Number(tenant.month_to_date_usage || 0) +
                                      Number(response.data.amount),
                                  last_activity_at: response.data.timestamp,
                              }
                            : tenant,
                    ),
                );

                setTenantSummary((prev) => {
                    if (!prev) return prev;
                    if (prev.tenant_id !== response.data.tenant_id) return prev;

                    return {
                        ...prev,
                        month_to_date_usage:
                            Number(prev.month_to_date_usage || 0) + Number(response.data.amount),
                        last_activity_at: response.data.timestamp,
                    };
                });
            }

            return {
                ok: true,
                replayed: response.data.idempotency_replayed,
                event: response.data,
            };
        } catch (error) {
            if (error.response?.status === 401) {
                onUnauthorized();
            }

            const status = error.response?.status;
            const responseData = error.response?.data;
            const message = responseData?.message;

            return {
                ok: false,
                message:
                    typeof message === 'string' && message.trim()
                        ? message
                        : `Failed to create event. Status ${status}.`,
            };
        }
    };

    const usageUsed = tenantSummary?.month_to_date_usage ?? 0;
    const usageQuota = tenantSummary?.configured_monthly_quota ?? 0;

    const dashboardTitle = isAdmin
        ? 'Admin Dashboard View'
        : `${auth?.user?.display_name || 'Tenant'} Dashboard`;

    const dashboardSubtitle = isAdmin
        ? 'Viewing platform-wide access with tenant management controls.'
        : `Logged in for tenant ${tenantScopedId}`;

    return (
        <div className="tenant-dashboard">
            <div className="dashboard-heading-block">
                <h1 className="dashboard-page-title">{dashboardTitle}</h1>
                <p className="dashboard-page-subtitle">{dashboardSubtitle}</p>
            </div>

            <div className="tenant-dashboard-top">
                <TokenCard used={usageUsed} total={usageQuota} />
                <EventForm
                    onSubmit={handleCreateEvent}
                    isAdmin={isAdmin}
                    auth={auth}
                    defaultTenantId={isAdmin ? selectedAdminTenantId : tenantScopedId || ''}
                    tenants={tenants}
                    onTenantChange={setSelectedAdminTenantId}
                />
            </div>

            <section className="usage-history-section">
                <h2>Events</h2>
                {loading ? <p>Loading...</p> : <UsageByDayTable events={events} />}
            </section>
        </div>
    );
}
