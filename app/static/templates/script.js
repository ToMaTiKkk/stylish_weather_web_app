document.addEventListener('DOMContentLoaded', () => {
    // динамич обновление года
    const currentYearSpan = document.getElementById('currentYear')
    if (currentYearSpan) {
        currentYearSpan.textContent = new Date().getFullYear();
    }
    
    const weatherForm = document.getElementById('weatherForm')
    const cityInput = document.getElementById('city')
    const weatherResultsSection = document.getElementById('weather-results-section')
    
    if (weatherForm) {
        weatherForm.addEventListener('submit', (event) => {
            event.preventDefault(); // блокируем стандартную отправку формы
            const cityName = cityInput.value.trim();
            
            if (cityName) {
                weatherResultsSection.innerHTML = `<p class="loading-text">Загрузка погоды для города ${cityName}...</p>`;
                console.log(`Запрос погоды для: ${cityName}`);
                // пока что имитируем задержку, потом переделается
                setTimeout(() => {
                    weatherResultsSection.innerHTML = `<p class="placeholder-text">Данные для "${cityName}" будут здесь (пока не реализовано).</p>`;
                }, 1500);
            } else {
                weatherResultsSection.innerHTML = `<p class="error-text">Пожалуйста, введите название города.</p>`;
            }
        });
    }
});