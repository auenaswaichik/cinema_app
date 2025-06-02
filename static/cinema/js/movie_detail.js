document.addEventListener('DOMContentLoaded', function() {
    // Обработка кнопок покупки билетов
    const buyButtons = document.querySelectorAll('.buy-ticket-btn');
    buyButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const sessionId = this.dataset.sessionId;
            if (!sessionId) {
                e.preventDefault();
                alert('Ошибка: не удалось определить сеанс');
            }
        });
    });

    // Обработка кнопок бронирования
    const bookButtons = document.querySelectorAll('.book-ticket-btn');
    bookButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const sessionId = this.dataset.sessionId;
            if (!sessionId) {
                e.preventDefault();
                alert('Ошибка: не удалось определить сеанс');
            }
        });
    });

    // Анимация карточек сеансов при наведении
    const sessionCards = document.querySelectorAll('.session-card');
    sessionCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Обработка формы отзыва
    const reviewForm = document.querySelector('#review-form');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            const rating = document.querySelector('#id_rating').value;
            const text = document.querySelector('#id_text').value;

            if (!rating || !text) {
                e.preventDefault();
                alert('Пожалуйста, заполните все поля формы');
            }
        });
    }

    // Обработка кнопки отмены бронирования
    const cancelButtons = document.querySelectorAll('.cancel-booking-btn');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Вы уверены, что хотите отменить бронирование?')) {
                e.preventDefault();
            }
        });
    });

    // Обработка таймера бронирования
    const bookingTimers = document.querySelectorAll('.booking-timer');
    bookingTimers.forEach(timer => {
        const expiryTime = new Date(timer.dataset.expiryTime).getTime();
        
        function updateTimer() {
            const now = new Date().getTime();
            const distance = expiryTime - now;

            if (distance < 0) {
                timer.innerHTML = 'Время бронирования истекло';
                return;
            }

            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            timer.innerHTML = `Осталось времени: ${minutes}м ${seconds}с`;
        }

        updateTimer();
        setInterval(updateTimer, 1000);
    });
}); 