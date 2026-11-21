class ApplicationError(Exception):
    status_code:int=500
    code:str="APPLICATION_ERROR"
    message:str="服务器内部错误"