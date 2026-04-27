import request from "@/utils/api";

export function getOpsCategories(params) {
  return request({
    url: "/ops-tools/categories/",
    method: "get",
    params,
  });
}

export function getActiveOpsCategories() {
  return request({
    url: "/ops-tools/categories/active/",
    method: "get",
  });
}

export function createOpsCategory(data) {
  return request({
    url: "/ops-tools/categories/",
    method: "post",
    data,
  });
}

export function updateOpsCategory(id, data) {
  return request({
    url: `/ops-tools/categories/${id}/`,
    method: "put",
    data,
  });
}

export function deleteOpsCategory(id) {
  return request({
    url: `/ops-tools/categories/${id}/`,
    method: "delete",
  });
}

export function getOpsEnvironments(params) {
  return request({
    url: "/ops-tools/environments/",
    method: "get",
    params,
  });
}

export function createOpsEnvironment(data) {
  return request({
    url: "/ops-tools/environments/",
    method: "post",
    data,
  });
}

export function updateOpsEnvironment(id, data) {
  return request({
    url: `/ops-tools/environments/${id}/`,
    method: "put",
    data,
  });
}

export function deleteOpsEnvironment(id) {
  return request({
    url: `/ops-tools/environments/${id}/`,
    method: "delete",
  });
}

export function importOpsEnvironments(items) {
  return request({
    url: "/ops-tools/environments/import/",
    method: "post",
    data: { items },
  });
}

export function testOpsEnvironmentConnection(id) {
  return request({
    url: `/ops-tools/environments/${id}/test-connection/`,
    method: "post",
  });
}

export function getOpsLogEnvironments() {
  return request({
    url: "/ops-tools/logs/environments/",
    method: "get",
  });
}

export function connectOpsLogEnvironment(data) {
  return request({
    url: "/ops-tools/logs/connect/",
    method: "post",
    data,
  });
}

export function disconnectOpsLogEnvironment(data) {
  return request({
    url: "/ops-tools/logs/disconnect/",
    method: "post",
    data,
  });
}

export function browseOpsLogDirectory(params) {
  return request({
    url: "/ops-tools/logs/browser/",
    method: "get",
    params,
  });
}

export function getOpsLogContent(params) {
  return request({
    url: "/ops-tools/logs/content/",
    method: "get",
    params,
  });
}

export function downloadOpsLogFile(params) {
  return request({
    url: "/ops-tools/logs/download/",
    method: "get",
    params,
    responseType: "blob",
  });
}
