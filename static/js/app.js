// ==========================================
// GLOBAL APPLICATION JAVASCRIPT
// ==========================================


document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupMobileMenu();

    }
);


// ==========================================
// MOBILE MENU
// ==========================================

function setupMobileMenu() {

    const button =
        document.getElementById(
            "mobileMenuBtn"
        );


    const nav =
        document.querySelector(
            ".nav-links"
        );


    if (!button || !nav) {

        return;

    }


    button.addEventListener(
        "click",
        function () {

            nav.classList.toggle(
                "mobile-open"
            );

        }
    );

}


// ==========================================
// NOTIFICATION
// ==========================================

function showNotification(
    message,
    type = "success"
) {

    const notification =
        document.createElement(
            "div"
        );


    notification.className =
        `notification ${type}`;


    notification.textContent =
        message;


    document.body.appendChild(
        notification
    );


    setTimeout(
        function () {

            notification.remove();

        },
        3000
    );

}