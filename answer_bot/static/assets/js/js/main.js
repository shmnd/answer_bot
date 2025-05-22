
    // Add active class to the current button (highlight it)

    $(document).ready(function () {
        $('.navbar-nav .nav-item .nav-link').click(function () {
            $('.nav-item .nav-link').removeClass("active");
            $(this).addClass("active");
        });
    });

    

    