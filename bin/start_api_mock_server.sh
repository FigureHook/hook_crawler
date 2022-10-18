OPENAPI_JSON_URL=https://raw.githubusercontent.com/FigureHook/hook_api/main/assets/openapi.json
MOCK_SERVER_IMAGE=stoplight/prism:4.10.3
OPENAPI_PATH=temp/openapi.json


if [ ! -f $OPENAPI_PATH ]; then
    echo "${OPENAPI_PATH} doesn't exists."
    echo "Pulling openapi spec file..."
    curl $OPENAPI_JSON_URL -o "${OPENAPI_PATH}"
fi

docker image inspect $MOCK_SERVER_IMAGE &>/dev/null

if [ $? -eq 1 ]; then
    echo "mocker serverz image was not found."
    echo "Start pulling the image..."
    docker pull $MOCK_SERVER_IMAGE
fi

docker run --init \
    -v "${PWD}/temp:/local" \
    -p 4010:4010 \
    $MOCK_SERVER_IMAGE \
    mock -h 0.0.0.0 "/local/openapi.json"
