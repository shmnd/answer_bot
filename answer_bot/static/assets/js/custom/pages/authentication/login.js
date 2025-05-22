"use strict";
let SigninGeneral = function () { // Elements
    let form;
    let submitButton;
    let validator;

    // Handle form
    const handleForm = function (e) {
        validator = FormValidation.formValidation(form, {
            fields: {
                'email': {
                    validators: {
                        notEmpty: {
                            message: 'Email address is required'
                        },
                        emailAddress: {
                            message: 'The value is not a valid email address'
                        }
                    }
                },
                'password': {
                    validators: {
                        notEmpty: {
                            message: 'The password is required'
                        }
                    }
                }
            },
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                bootstrap: new FormValidation.plugins.Bootstrap5(
                    { rowSelector: '.fv-row' }
                )
            }
        });

// Handle form submit
submitButton.addEventListener('click', function (e) {
    // Prevent button default action
    e.preventDefault();

    // Validate form
    validator.validate().then(function (status) {
        if (status == 'Valid') { // Show loading indication
            submitButton.setAttribute('data-kt-indicator', 'on');

            // Disable button to avoid multiple clicks
            submitButton.disabled = true;

            // Get email and password from the form
            let email = form.querySelector('[name="email"]').value;
            let password = form.querySelector('[name="password"]').value;

            // Simulate ajax request
            $.post(`${api_config.authentication_url}`, {
                email: email,
                password: password
            }, function (data, status, xhr) {
                // console.log(data)
                if (data.status_code == 100) { // Check for a successful HTTP status code (e.g., 200)
                    // Show success Swal alert without the "Ok" button
                    Swal.fire({
                        text: data.message,
                        icon: "success",
                        buttonsStyling: false,
                        showConfirmButton: false, // Remove the "Ok" button
                        timer: 1300, // Auto close the alert after 2 seconds (adjust as needed)
                        customClass: {
                            confirmButton: "btn btn-primary"
                        }
                    }).then(function (result) {
                        if (result.dismiss === Swal.DismissReason.timer) {
                            // Redirect to the specified URL after success (if needed)
                            let redirectUrl = form.getAttribute('data-redirect-url');
                            if (redirectUrl) {
                                location.href = redirectUrl;
                            }
                            // Enable the submit button after success
                            submitButton.disabled = false;
                        }
                    });
                } else {
                    // Show error Swal alert
                    Swal.fire({
                        text: data.message,
                        icon: "error",
                        buttonsStyling: false,
                        confirmButtonText: "Ok, got it!",
                        customClass: {
                            confirmButton: "btn btn-primary"
                        }
                    });
                    // Enable the submit button after an error
                    submitButton.disabled = false;
                }
            }, 'json').done(function () {
                submitButton.removeAttribute('data-kt-indicator');

            }).fail(function (jqxhr, settings, e) {
                console.log('failed, ' + e);
                // Enable the submit button on request failure
                submitButton.disabled = false;
            });
        } else {
            Swal.fire({
                text: "Sorry, looks like there are some errors detected, please try again.",
                icon: "error",
                buttonsStyling: false,
                confirmButtonText: "Ok, got it!",
                customClass: {
                    confirmButton: "btn btn-primary"
                }
            });
        }
    });
});

    }

    // Public functions
    return { // Initialization
        init: function () {
            form = document.querySelector('#_sign_in_form');
            submitButton = document.querySelector('#_sign_in_submit');
            // console

            handleForm();
        }
    };
}();

KTUtil.onDOMContentLoaded(function () {
    SigninGeneral.init();
});
