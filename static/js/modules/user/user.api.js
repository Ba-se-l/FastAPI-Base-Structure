/**
 * User Module API Client
 */
import { httpClient } from '../../core/http-client.js';

export async function getMe() {
    return await httpClient.get('/api/v1/users/me');
}

export async function listUsers(page = 1, pageSize = 10) {
    return await httpClient.get(`/api/v1/users?page=${page}&page_size=${pageSize}`);
}

export async function getUser(userId) {
    return await httpClient.get(`/api/v1/users/${userId}`);
}

export async function updateUser(userId, data) {
    return await httpClient.patch(`/api/v1/users/${userId}`, data);
}
