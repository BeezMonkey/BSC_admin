from django.shortcuts import render

from accounts.decorators import coordinator_required


@coordinator_required
def coordinator_dashboard(request):
    return render(request, "coordinators/sc_dashboard.html")
