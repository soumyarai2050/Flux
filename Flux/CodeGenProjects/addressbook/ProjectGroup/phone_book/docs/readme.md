FastAPI
1. To view FastAPI generated JSON (schema) with the descriptions of all generated API:
`http://127.mobile_book.mobile_book.1:8mobile_bookmobile_bookmobile_book/openapi.json`
2. Path , EndPoint and Route are use interchangeably in the documentation
3. add path params or vars with py f"str{var}" syntax 
4. Refer generated documentation from /docs and /redoc suffix urls
5. route definition order matters, first matching route is opted, eg: 
   - if first route declared is: `/users/{user_id}`
   - second declared route is: `/users/me` 
     - the specific route declared (second: `/users/me`) will never be called as first route is always a match
6. declaring non path function params are interpreted as "query" params
7. query is the set of key-value pairs that go after `?` in URL, separated by `&`
   - http://127.mobile_book.mobile_book.1:8mobile_bookmobile_bookmobile_book/items/?skip=mobile_book&limit=1mobile_book
8. optional query parameters: `async def read_item(item_id: str, q: str | None = None):`
9. To send data use: POST (the more common), PUT, DELETE or PATCH. Sending body with GET is undefined behavior in spec
   - nevertheless, it's supported by FastAPI - (docs) Swagger UI won't show body documentation for such GETs. 
   - Proxies in middle might not support it (so it's best to align with standard behaviour)
