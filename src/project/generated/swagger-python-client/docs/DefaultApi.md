# swagger_client.DefaultApi

All URIs are relative to *http://{host}:{port}*

Method | HTTP request | Description
------------- | ------------- | -------------
[**config_get**](DefaultApi.md#config_get) | **GET** /config | Get current configuration
[**config_post**](DefaultApi.md#config_post) | **POST** /config | Set configuration
[**config_set_get**](DefaultApi.md#config_set_get) | **GET** /config/set | Set configuration via query params
[**root_get**](DefaultApi.md#root_get) | **GET** / | Health check
[**status_get**](DefaultApi.md#status_get) | **GET** /status | Get current device status


# **config_get**
> ConfigResponse config_get()

Get current configuration

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.DefaultApi()

try:
    # Get current configuration
    api_response = api_instance.config_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->config_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**ConfigResponse**](ConfigResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **config_post**
> ConfigSetResponse config_post(body)

Set configuration

Sets the reading interval; optionally persists to settings.toml.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure API key authorization: ApiKeyAuth
configuration = swagger_client.Configuration()
configuration.api_key['x-api-key'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['x-api-key'] = 'Bearer'

# create an instance of the API class
api_instance = swagger_client.DefaultApi(swagger_client.ApiClient(configuration))
body = swagger_client.ConfigSetRequest() # ConfigSetRequest | 

try:
    # Set configuration
    api_response = api_instance.config_post(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->config_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ConfigSetRequest**](ConfigSetRequest.md)|  | 

### Return type

[**ConfigSetResponse**](ConfigSetResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **config_set_get**
> ConfigSetResponse config_set_get(interval, persist=persist)

Set configuration via query params

Convenience endpoint to set interval via query string.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure API key authorization: ApiKeyAuth
configuration = swagger_client.Configuration()
configuration.api_key['x-api-key'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['x-api-key'] = 'Bearer'

# create an instance of the API class
api_instance = swagger_client.DefaultApi(swagger_client.ApiClient(configuration))
interval = 56 # int | 
persist = 'persist_example' # str |  (optional)

try:
    # Set configuration via query params
    api_response = api_instance.config_set_get(interval, persist=persist)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->config_set_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **interval** | **int**|  | 
 **persist** | **str**|  | [optional] 

### Return type

[**ConfigSetResponse**](ConfigSetResponse.md)

### Authorization

[ApiKeyAuth](../README.md#ApiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **root_get**
> str root_get()

Health check

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.DefaultApi()

try:
    # Health check
    api_response = api_instance.root_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->root_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

**str**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **status_get**
> StatusResponse status_get()

Get current device status

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.DefaultApi()

try:
    # Get current device status
    api_response = api_instance.status_get()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling DefaultApi->status_get: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**StatusResponse**](StatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

