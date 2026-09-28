from src.exc import AppException, NotFoundException, AlreadyExistsException, InactiveEntityException


class UserNotFoundException(NotFoundException):
    def __init__(self, identifier : str):
        super().__init__(entity="User", identifier=identifier)

class UserAlreadyExistsException(AlreadyExistsException):
    def __init__(self, field : str, value : str):
        super().__init__(entity="User", field=field, value=value)

class UserInactiveException(InactiveEntityException):
    def __init__(self, identifier : str):
        super().__init__(entity="User", identifier=identifier)

