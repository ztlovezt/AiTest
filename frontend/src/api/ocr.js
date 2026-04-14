/**
 * OCR 服务相关 API
 */
import request from '@/utils/api'

export function getOCRConfigs(params) {
  return request({
    url: '/ocr/configs/',
    method: 'get',
    params
  })
}

export function getOCRConfigDetail(id) {
  return request({
    url: `/ocr/configs/${id}/`,
    method: 'get'
  })
}

export function createOCRConfig(data) {
  return request({
    url: '/ocr/configs/',
    method: 'post',
    data
  })
}

export function updateOCRConfig(id, data) {
  return request({
    url: `/ocr/configs/${id}/`,
    method: 'patch',
    data
  })
}

export function deleteOCRConfig(id) {
  return request({
    url: `/ocr/configs/${id}/`,
    method: 'delete'
  })
}

export function setDefaultOCRConfig(id) {
  return request({
    url: `/ocr/configs/${id}/set_default/`,
    method: 'post'
  })
}

export function getActiveOCRConfigs() {
  return request({
    url: '/ocr/configs/active/',
    method: 'get'
  })
}

export function testOCRConfig(id, testData) {
  return request({
    url: `/ocr/configs/${id}/test/`,
    method: 'post',
    data: testData
  })
}

export function recognizeImage(data) {
  return request({
    url: '/ocr/recognize/',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
