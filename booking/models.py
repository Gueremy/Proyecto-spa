# En tu archivo models.py

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

# Modelo para los cupones de descuento
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.PositiveIntegerField(help_text="Porcentaje de descuento (e.g., 10 para 10%)")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField()
    valid_to = models.DateField()

    def __str__(self):
        return self.code

    def is_valid(self):
        today = timezone.now().date()
        return self.is_active and self.valid_from <= today <= self.valid_to

class Reserva(models.Model):
    # --- Campos existentes ---
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=200)
    fecha = models.DateField()
    dias = models.PositiveIntegerField("Cantidad de días", default=1)
    espacio_techado = models.BooleanField("¿Cuenta con espacio de 2x2mt techado?", default=False)
    pagado = models.BooleanField(default=False)

    # --- Nuevos campos ---
    numero_reserva = models.CharField(max_length=10, editable=False, unique=True, blank=True)
    total = models.DecimalField("Total", max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    def clean(self):
        # Validación para no permitir reservas en fechas pasadas
        if self.fecha and self.fecha < timezone.now().date():
            raise ValidationError("No se pueden crear reservas para fechas pasadas.")

    def save(self, *args, **kwargs):
        # Generar número de reserva único si es una nueva reserva
        if not self.pk:
            self.numero_reserva = uuid.uuid4().hex[:8].upper()
        
        # Calcular el total con la lógica de precios por tramos
        if self.dias == 1:
            self.total = 35000
        elif self.dias >= 2:
            self.total = self.dias * 25000
        else:
            self.total = 0 # Opcional: manejar el caso de 0 días
        
        # Aplicar descuento si hay un cupón válido
        if self.coupon and self.coupon.is_valid():
            descuento = (self.total * self.coupon.discount_percentage) / 100
            self.total -= descuento

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} - {self.numero_reserva}"

class DiaFeriado(models.Model):
    fecha = models.DateField(unique=True)
    descripcion = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.fecha} - {self.descripcion}"