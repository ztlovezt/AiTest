import * as curlconverter from 'curlconverter'

export interface RequestModel {
  method: string
  baseURL: string
  path: string
  query: QueryParam[]
  headers: Header[]
  body: Body
  auth?: Auth
  timeout?: number
}

export interface QueryParam {
  key: string
  value: string
  enabled: boolean
}

export interface Header {
  key: string
  value: string
  enabled: boolean
}

export interface Body {
  mode: 'none' | 'raw' | 'json' | 'formdata' | 'urlencoded' | 'binary'
  raw?: string
  json?: string
  formdata?: FormField[]
  urlencoded?: FormField[]
  binary?: File
}

export interface FormField {
  key: string
  value: string
  type: 'text' | 'file'
  enabled: boolean
}

export interface Auth {
  type: 'none' | 'basic' | 'bearer' | 'api_key'
  username?: string
  password?: string
  token?: string
  key?: string
  value?: string
  addTo?: 'header' | 'query'
}

export class RequestModelParser {
  static async parseCurl(curlCommand: string): Promise<RequestModel> {
    try {
      const harData = curlconverter.toHarString(curlCommand)
      const har = JSON.parse(harData)
      
      if (!har.log || !har.log.entries || har.log.entries.length === 0) {
        throw new Error('无法解析CURL命令，请检查格式')
      }
      
      const entry = har.log.entries[0]
      const request = entry.request
      
      // console.log('HAR request URL:', request.url)
      // console.log('HAR request queryString:', request.queryString)
      
      const url = new URL(request.url)
      let baseURL = `${url.protocol}//${url.host}`
      const path = url.pathname
      
      // 如果原始cURL命令中没有协议前缀，说明是curlconverter自动补全的，我们需要还原
      // 特别是为了保留 {{host}} 等环境变量
      if (baseURL.startsWith('http://') && !curlCommand.includes(baseURL)) {
        const stripped = baseURL.substring(7) // 移除 'http://'
        if (curlCommand.includes(stripped)) {
          baseURL = stripped
        }
      } else if (baseURL.startsWith('https://') && !curlCommand.includes(baseURL)) {
        const stripped = baseURL.substring(8) // 移除 'https://'
        if (curlCommand.includes(stripped)) {
          baseURL = stripped
        }
      }
      
      const query: QueryParam[] = []
      
      if (request.queryString && request.queryString.length > 0) {
        request.queryString.forEach((param: any) => {
          query.push({ key: param.name, value: param.value || '', enabled: true })
        })
      } else {
        url.searchParams.forEach((value, key) => {
          query.push({ key, value, enabled: true })
        })
      }
      
      // console.log('Parsed URL:', { baseURL, path, search: url.search, searchParams: Array.from(url.searchParams.entries()), query })
      
      const headers: Header[] = []
      
      if (request.cookies && request.cookies.length > 0) {
        const cookieValue = request.cookies
          .map((cookie: any) => `${cookie.name}=${cookie.value}`)
          .join('; ')
        headers.push({ key: 'Cookie', value: cookieValue, enabled: true })
      }
      
      request.headers.forEach((header: any) => {
        headers.push({ key: header.name, value: header.value, enabled: true })
      })
      
      // console.log('HAR headers:', request.headers)
      // console.log('HAR cookies:', request.cookies)
      // console.log('Parsed headers:', headers)
      
      const body: Body = { mode: 'none' }
      const contentType = headers.find(h => h.key.toLowerCase() === 'content-type')?.value
      
      if (request.postData) {
        const postData = request.postData
        
        if (contentType?.includes('application/json')) {
          body.mode = 'json'
          body.json = postData.text || ''
        } else if (contentType?.includes('application/x-www-form-urlencoded')) {
          body.mode = 'urlencoded'
          body.urlencoded = []
          if (postData.params) {
            postData.params.forEach((param: any) => {
              body.urlencoded?.push({ 
                key: param.name, 
                value: param.value || '', 
                type: 'text', 
                enabled: true 
              })
            })
          }
        } else if (contentType?.includes('multipart/form-data')) {
          body.mode = 'formdata'
          body.formdata = []
          if (postData.params) {
            postData.params.forEach((param: any) => {
              body.formdata?.push({
                key: param.name,
                value: param.value || param.fileName || '',
                type: param.fileName ? 'file' : 'text',
                enabled: true
              })
            })
          }
        } else {
          body.mode = 'raw'
          body.raw = postData.text || ''
        }
      } else if (contentType) {
        if (contentType.includes('application/json')) {
          body.mode = 'json'
          body.json = ''
        } else if (contentType.includes('application/x-www-form-urlencoded')) {
          body.mode = 'urlencoded'
          body.urlencoded = []
        } else if (contentType.includes('multipart/form-data')) {
          body.mode = 'formdata'
          body.formdata = []
        } else {
          body.mode = 'raw'
          body.raw = ''
        }
      }
      
      return {
        method: request.method || 'GET',
        baseURL,
        path,
        query,
        headers,
        body,
        auth: RequestModelParser.parseAuth(headers),
        timeout: 30000
      }
    } catch (error: any) {
      console.error('Failed to parse cURL command:', error)
      console.error('cURL command:', curlCommand)
      const errorMessage = error?.message || error?.toString() || 'Unknown error'
      throw new Error(`cURL命令解析失败: ${errorMessage}，请检查命令格式`)
    }
  }
  
  static parseAuth(headers: Header[]): Auth | undefined {
    const authHeader = headers.find(h => h.key.toLowerCase() === 'authorization')
    if (authHeader) {
      const value = authHeader.value
      
      if (value.startsWith('Bearer ')) {
        return {
          type: 'bearer',
          token: value.substring(7)
        }
      }
      
      if (value.startsWith('Basic ')) {
        try {
          const decoded = atob(value.substring(6))
          const [username, password] = decoded.split(':')
          return {
            type: 'basic',
            username,
            password
          }
        } catch {
          return undefined
        }
      }
    }
    
    return undefined
  }
  
  static toCurl(model: RequestModel): string {
    let curl = `curl -X ${model.method}`
    
    let urlString = ''
    if (model.baseURL && model.path) {
      urlString = model.baseURL + model.path
    } else if (model.baseURL) {
      urlString = model.baseURL
    } else if (model.path) {
      urlString = model.path
    } else {
      throw new Error('Invalid URL: both baseURL and path are empty')
    }
    
    const activeParams = model.query.filter(p => p.enabled && p.key)
    if (activeParams.length > 0) {
      try {
        const urlObj = new URL(urlString)
        activeParams.forEach(param => {
          urlObj.searchParams.append(param.key, param.value)
        })
        urlString = urlObj.toString()
      } catch (e) {
        // Fallback for invalid URLs like variables {{host}}/api or relative paths /api
        const separator = urlString.includes('?') ? '&' : '?'
        const paramsString = activeParams.map(p => `${encodeURIComponent(p.key)}=${encodeURIComponent(p.value)}`).join('&')
        urlString += separator + paramsString
      }
    }
    
    curl += ` '${urlString}'`
    
    model.headers.forEach(header => {
      if (header.enabled && header.key) {
        curl += ` -H '${header.key}: ${header.value}'`
      }
    })
    
    // 如果用户没有显式设置 Content-Type，则根据 body 类型自动补充
    const hasContentType = model.headers.some(h => h.enabled && h.key && h.key.toLowerCase() === 'content-type')
    if (!hasContentType) {
      if (model.body.mode === 'json') {
        curl += ` -H 'Content-Type: application/json'`
      } else if (model.body.mode === 'urlencoded') {
        curl += ` -H 'Content-Type: application/x-www-form-urlencoded'`
      } else if (model.body.mode === 'raw') {
        curl += ` -H 'Content-Type: text/plain'`
      }
      // 注意：formdata 时，curl 的 -F 参数会自动生成带有 boundary 的 multipart/form-data，不需要显式指定
    }
    
    if (model.body.mode === 'json' && model.body.json) {
      curl += ` -d '${model.body.json.replace(/'/g, "'\\''")}'`
    } else if (model.body.mode === 'raw' && model.body.raw) {
      curl += ` -d '${model.body.raw.replace(/'/g, "'\\''")}'`
    } else if (model.body.mode === 'urlencoded' && model.body.urlencoded) {
      model.body.urlencoded.forEach(field => {
        if (field.enabled && field.key) {
          curl += ` --data-urlencode '${field.key}=${field.value.replace(/'/g, "'\\''")}'`
        }
      })
    } else if (model.body.mode === 'formdata' && model.body.formdata) {
      model.body.formdata.forEach(field => {
        if (field.enabled && field.key) {
          if (field.type === 'file') {
            curl += ` -F '${field.key}=@${field.value.replace(/'/g, "'\\''")}'`
          } else {
            curl += ` -F '${field.key}=${field.value.replace(/'/g, "'\\''")}'`
          }
        }
      })
    }
    
    if (model.timeout) {
      curl += ` --max-time ${model.timeout / 1000}`
    }
    
    return curl
  }
  
  static toFormData(model: RequestModel): FormData {
    const formData = new FormData()
    
    if (model.body.mode === 'formdata' && model.body.formdata) {
      model.body.formdata.forEach(field => {
        if (field.enabled && field.key) {
          if (field.type === 'file' && field.value) {
            formData.append(field.key, field.value as any)
          } else {
            formData.append(field.key, field.value)
          }
        }
      })
    }
    
    return formData
  }
  
  static toURLSearchParams(model: RequestModel): URLSearchParams {
    const params = new URLSearchParams()
    
    if (model.body.mode === 'urlencoded' && model.body.urlencoded) {
      model.body.urlencoded.forEach(field => {
        if (field.enabled && field.key) {
          params.append(field.key, field.value)
        }
      })
    }
    
    return params
  }
}
