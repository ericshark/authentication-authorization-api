3/23/26:
-The event loop is the main thread running on one instance of your backend instance (can be multiple if multiple cores through gunicorn)
-The event loop recieves all the requests and then if its async completes the function because it sends a request to external worker so its non blocking
-If the event loop recieves a sync function request it offloads in to a thread which is a seperate