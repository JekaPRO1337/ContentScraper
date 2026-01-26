// Main JS - Interactions

// Smooth scroll for anchors
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Setup observer for fade-in elements
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, { threshold: 0.1 });

// Add animation classes
document.querySelectorAll('.card, .hero-content').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
    observer.observe(el);
});

// Animation logic
const animate = () => {
    document.querySelectorAll('.visible').forEach(el => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
    });
    requestAnimationFrame(animate);
};
animate();

// Mobile Menu Toggle
const menuToggle = document.querySelector('.menu-toggle');
const links = document.querySelector('.links');

if (menuToggle && links) {
    menuToggle.addEventListener('click', () => {
        menuToggle.classList.toggle('active');
        links.classList.toggle('active');
    });

    // Close menu when clicking on a link
    document.querySelectorAll('.links a').forEach(link => {
        link.addEventListener('click', () => {
            menuToggle.classList.remove('active');
            links.classList.remove('active');
        });
    });
}

