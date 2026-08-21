from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def criar_hash(senha):
    return pwd_context.hash(senha)


def verificar_senha(senha, senha_hash):
    return pwd_context.verify(senha, senha_hash)