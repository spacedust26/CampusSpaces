from django.shortcuts import render

def index(request):
    return render(request, 'home/index.html')

def dashboard(request):
    return render(request, 'home/dashboard.html')

def view_space(request):
    return render(request, 'home/view_space.html')

def view_equipment(request):
    return render(request, 'home/view_equipment.html')

def booking_cart(request):
    return render(request, 'home/booking_cart.html')

def history(request):
    return render(request, 'home/history.html')