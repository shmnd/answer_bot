"use strict";
let SignupGeneral = function () { 
    let form;
    let submitButton;
    let validator;

    function getCSRFToken() {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            document.cookie.split(";").forEach(function (cookie) {
                let trimmedCookie = cookie.trim();
                if (trimmedCookie.startsWith("csrftoken=")) {
                    cookieValue = trimmedCookie.substring("csrftoken=".length);
                }
            });
        }
        return cookieValue;
    }

    const handleForm = function () {
        validator = FormValidation.formValidation(form, {
            fields: {
                'email': {
                    validators: {
                        notEmpty: { message: 'Email address is required' },
                        emailAddress: { message: 'The value is not a valid email address' }
                    }
                },
      
                'password': {
                    validators: {
                        notEmpty: { message: 'Password is required' },
                        stringLength: {
                            min: 6,
                            message: 'Password must be at least 6 characters long'
                        }
                    }
                },
                'confirm_password': {
                    validators: {
                        notEmpty: { message: 'Confirm password is required' },
                        identical: {
                            compare: function () {
                                return form.querySelector('[name="password"]').value;
                            },
                            message: 'Passwords do not match'
                        }
                    }
                }
            },
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                bootstrap: new FormValidation.plugins.Bootstrap5({ rowSelector: '.fv-row' })
            }
        });

        submitButton.addEventListener('click', function (e) {
            e.preventDefault();

            validator.validate().then(function (status) {
                if (status == 'Valid') { 
                    submitButton.setAttribute('data-kt-indicator', 'on');
                    submitButton.disabled = true;

                    let email = form.querySelector('[name="email"]').value;
                    let password = form.querySelector('[name="password"]').value;
                    let confirmPassword = form.querySelector('[name="confirm_password"]').value;

                    $.post(form.action, {  // ✅ Ensure form action is correct
                        email: email,
                        password: password,
                        confirm_password: confirmPassword,
                        csrfmiddlewaretoken: getCSRFToken()
                    }, function (data, status, xhr) {
                        if (data.status_code == 100) {
                            Swal.fire({
                                text: data.message,
                                icon: "success",
                                buttonsStyling: false,
                                showConfirmButton: false, 
                                timer: 1300,
                                customClass: { confirmButton: "btn btn-primary" }
                            }).then(function () {
                                console.log("Redirecting to:", data.redirect_url);  // ✅ Debugging line
                                if (data.redirect_url) {
                                    window.location.href = data.redirect_url;  // ✅ Perform the redirect
                                }
                            });
                        } else {
                            Swal.fire({
                                text: data.message,
                                icon: "error",
                                buttonsStyling: false,
                                confirmButtonText: "Ok, got it!",
                                customClass: { confirmButton: "btn btn-primary" }
                            });
                        }
                    }, 'json')
                    .fail(function (jqxhr, settings, e) {  
                        let errorResponse = jqxhr.responseJSON;  
                        let errorMessage = "Something went wrong. Please try again.";

                        if (errorResponse) {
                            if (errorResponse.message) {
                                errorMessage = errorResponse.message;  
                            }
                            if (errorResponse.error) {
                                console.error("Backend Error:", errorResponse.error);  
                            }
                        }

                        Swal.fire({
                            text: errorMessage,
                            icon: "error",
                            buttonsStyling: false,
                            confirmButtonText: "Ok, got it!",
                            customClass: { confirmButton: "btn btn-primary" }
                        });

                        submitButton.disabled = false;
                    });
                } else {
                    Swal.fire({
                        text: "Please fix the errors and try again.",
                        icon: "error",
                        buttonsStyling: false,
                        confirmButtonText: "Ok, got it!",
                        customClass: { confirmButton: "btn btn-primary" }
                    });
                }
            });
        });
    };

    return { 
        init: function () {
            form = document.querySelector('#_sign_up_form');
            submitButton = document.querySelector('#_sign_up_submit');

            if (form && submitButton) {
                handleForm();
            }
        }
    };
}();

KTUtil.onDOMContentLoaded(function () {
    SignupGeneral.init();
});
