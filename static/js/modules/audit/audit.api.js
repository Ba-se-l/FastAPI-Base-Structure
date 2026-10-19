/**
 * Audit Module API Client
 */
import { httpClient } from '../../core/http-client.js';

export async function listAuditLogs(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return await httpClient.get(`/api/v1/audit/logs?${qs}`);
}

export async function getAuditLog(logId) {
    return await httpClient.get(`/api/v1/audit/logs/${logId}`);
}

export async function exportAuditLogs(format = 'json', params = {}) {
    const qs = new URLSearchParams({ ...params, format }).toString();
    return await httpClient.get(`/api/v1/audit/export?${qs}`, { isBlob: false });
}
