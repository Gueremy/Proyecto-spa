from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.reservation_form, name='reservation_form'),
    path('success/<int:reserva_id>/', views.reservation_success, name='reservation_success'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/editar/<int:reserva_id>/', views.editar_reserva, name='editar_reserva'),
    path('admin-panel/eliminar/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),
    path('admin-panel/agregar-feriado/', views.agregar_feriado, name='agregar_feriado'),
    path('admin-panel/eliminar-feriado/<int:feriado_id>/', views.eliminar_feriado, name='eliminar_feriado'),
    path('admin-panel/agregar-cupon/', views.agregar_cupon, name='agregar_cupon'),
    path('admin-panel/eliminar-cupon/<int:coupon_id>/', views.eliminar_cupon, name='eliminar_cupon'),
    path('admin-panel/export/excel/', views.export_reservas_excel, name='export_reservas_excel'),
    path('admin-panel/export/pdf/', views.export_reservas_pdf, name='export_reservas_pdf'),
]