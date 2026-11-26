"""Asistente de consulta con procedencia visible y correcciones comunitarias."""
from .asistente import Asistente, Respuesta
from .correcciones import ErrorCorreccion, RegistroCorrecciones

__all__ = ["Asistente", "Respuesta", "RegistroCorrecciones", "ErrorCorreccion"]
