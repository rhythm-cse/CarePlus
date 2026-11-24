
// =====================================
// CAREPLUS - MAIN JAVASCRIPT
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    // Display welcome message in browser console
    console.log("Welcome to CarePlus Healthcare System!");

    // Smooth scrolling for internal page links
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {

        link.addEventListener("click", function (event) {

            const target = document.querySelector(this.getAttribute("href"));

            if (target) {
                event.preventDefault();

                target.scrollIntoView({
                    behavior: "smooth"
                });
            }
        });
    });

});
// Doctors Page: Search and Filter
document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("doctorSearch");
    const specialtyFilter = document.getElementById("specialtyFilter");
    const clearButton = document.getElementById("clearFilters");
    const doctorItems = document.querySelectorAll(".doctor-item");
    const count = document.getElementById("doctorCount");
    const noDoctors = document.getElementById("noDoctors");

    // Run only on the Doctors page
    if (!searchInput || !specialtyFilter || !clearButton) {
        return;
    }

    function filterDoctors() {

        const searchTerm = searchInput.value.trim().toLowerCase();
        const selectedSpecialty = specialtyFilter.value.toLowerCase();

        let visibleCount = 0;

        doctorItems.forEach(function (item) {

            const name = (item.dataset.name || "").toLowerCase();
            const city = (item.dataset.city || "").toLowerCase();
            const specialty = (item.dataset.specialty || "").toLowerCase();

            const matchesSearch =
                name.includes(searchTerm) || city.includes(searchTerm);

            const matchesSpecialty =
                selectedSpecialty === "" || specialty === selectedSpecialty;

            const shouldShow = matchesSearch && matchesSpecialty;

            item.style.display = shouldShow ? "" : "none";

            if (shouldShow) {
                visibleCount++;
            }
        });

        count.textContent = `Showing ${visibleCount} doctors`;
        noDoctors.style.display = visibleCount === 0 ? "block" : "none";
    }

    searchInput.addEventListener("input", filterDoctors);
    specialtyFilter.addEventListener("change", filterDoctors);

    clearButton.addEventListener("click", function () {
        searchInput.value = "";
        specialtyFilter.value = "";
        filterDoctors();
    });

});