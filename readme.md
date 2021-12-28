<p align="center" style="font-size: 3em;">RequestMap</p>

<p>RequestMap is a Python3 microframework designed with compatibility and portability in mind. It utilises a plugin-based system to allow your application to easily integrate with other frameworks such as Flask without the need of changing the code. <a href="https://yyjlincoln.com/requestmap">Website.</a></p>

## Installing RequestMap

RequestMap is not published on pip yet as it's currently under development. With that in mind, you can add it to your project by following the instructions below.

### In your project folder, cloning the repository

```bash
git clone https://github.com/yyjlincoln/RequestMap
```

### Then, install the dependencies

```bash
python3 -m pip install -r requirements.txt
```

### Finally, add requestmap as a submodule

```bash
git submodule add https://github.com/yyjlincoln/RequestMap RequestMap
```

### Learn more about submodules

You might wish to learn more about git submodules [here](https://git-scm.com/book/en/v2/Git-Tools-Submodules).

## The Concepts of RequestMap

RequestMap uses a plugin-based system. It consists of three main components:

- Protocol
- ResponseHandler
- Validator

### Protocol

A `Protocol` is the part of the plugin that handles incoming requests and pass it down to RequestMap's internal handlers. An instance of `RequestMap` (aka `EndpointMap`) can have multiple protocols registered. A protocol must inherit from `RequestMap.Protocols.ProtocolBase.StandardProtocolHandler`.

You can use a `Protocol` through:

```python
from RequestMap import Map
# Initialise an instance of RequestMap (aka EndpointMap)
API = Map()

# Initialise the protocol instance
SomeProtocolInstance = SomeProtocol(someConfiguration=1, anotherConfiguration=True)

# Use the protocol
API.useProtocol(SomeProtocolInstance)
```

For more on `Protocol`, check out `RequestMap.Protocols.ProtocolBase.StandardProtocolHandler`.

### ResponseHandler

A `ResponseHandler` is an optional function that standardises the response from your view function. An instance of `RequestMap` (aka `EndpointMap`) can only have ONE ResponseHandler. It must inherit from `RequestMap.Response.ResponseBase.StandardResponseHandler`.

The `ResponseHandler` can be obtained in a view function by specifying a `makeResponse` keyword-only argument. For example:

```python
@API.endpoint('addition', {
    'authrequired': False,
    'httproute': '/addition',
    'httpmethods': ['GET']
}, a=float, b=float)
def addition(a, b, makeResponse):
    return makeResponse(code=0, message="succeeded", result=a+b)
```

### Validator

A `Validator` validates the incoming request. This can be useful for authentication purposes (for example, by validating userId and token and rejecting the request by throwing `RequestMap.Exceptions.ValidationError` if the credentials are invalid). It must inherit from `RequestMap.Validators.ValidatorBase.StandardValidator`.

For more on `Validator`, check out `RequestMap.Validators.ValidatorBase.StandardValidator`

## Using RequestMap

### Setting up an endpoint

You can set up an endpoint using the decorator, `RequestMap.EndpointMap.Map().endpoint()`. For simplicity, we'll call `RequestMap.EndpointMap.Map()`, which is an instance, "`API` (initialised above)".

#### `@API.endpoint(<endpointIdentifier>, metadata = {}, **TypeConversionFunctions)` [Decorator]

- `endpointIdentifier`: The identifier of the endpoint. It must be unique.

- `metadata`: A dictionary of metadata about the endpoint. This is available to `Validator`s so you can configure the `Validator` on a per-route basis.

- **`TypeConversionFunctions`: Keyword arguments that specify the type conversion functions for the data of the endpoint. It follows a format of `<dataName>=<callable>`, for example, `aNumber=float`. If dataName does not exist in the data then the conversion function will not be called; otherwise it will be called and the data of that key will be replaced by the return value of the type conversion function.

#### `def theViewFunction(<nonOptionalArgs>, <optionalArgsWithDefaultValue> = <defaultValue>):`

Following the decorator, the view function can specify which data is required and which are optional. `RequestMap` will automatically retrieve the values from the request, convert it using the type conversion functions, and pass it to the view function. If the data does not exist and it's nonOptional, then an `Exceptions.MissingParameter` exception will be raised which can be captured by the `responseHandler` function.

## Lifecycle & Internal Logic

<img src="https://static.yyjlincoln.com/docs/RequestMap/logic.svg">

Alternatively, you can view the PNG version of this flowchart [here](https://static.yyjlincoln.com/docs/RequestMap/logic.png)

## Example

```python
from utils.RequestMap.Protocols.Flask import HTTPViaFlask
from utils.RequestMap.Response.JSON import JSONStandardizer

API.useProtocol(FlaskProtocol(port=5000, ALLOW_DEV_SERVER=True)) # Launches the dev server. For production, use FlaskProtocol().app with programs such as Gunicorn. 
API.useResponseHandler(JSONStandardizer({
    0: "succeeded",
    -1: "failed",
    -2: "unauthorised",
})

@API.endpoint('addition', {
    'authrequired': False,
    'httproute': '/addition',
    'httpmethods': ['GET']
}, a=float, b=float)
def addition(a, b, makeResponse):
    return makeResponse(code=0, result=a+b)
```

## See it in action

The `RequestMap` framework is used by a few projects. Check them out here:

- [NowAskMe-Server](https://github.com/yyjlincoln/NowAskMe-Server)
- [Time2Meet-Server](https://github.com/time2meet/time2meet-server)

## License

RequestMap is licensed under the [Apache License 2.0
](https://github.com/yyjlincoln/RequestMap/blob/master/LICENSE).

Copyright @yyjlincoln
