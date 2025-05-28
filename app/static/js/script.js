document.addEventListener('DOMContentLoaded', () => {
    // динамич обновление года
    const currentYearSpan = document.getElementById('currentYear')
    if (currentYearSpan) {
        currentYearSpan.textContent = new Date().getFullYear();
    }
    
    const weatherForm = document.getElementById('weatherForm')
    const cityInput = document.getElementById('city')
    const weatherResultsSection = document.getElementById('weather-results-section')
    // от main.py 
    const WMO_CODES = typeof WMO_CODES_FROM_SERVER !== "undefined" ? WMO_CODES_FROM_SERVER : {};
    
    if (weatherForm) {
        weatherForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // блокируем стандартную отправку формы
            const cityName = cityInput.value.trim();
            
            if (!cityName) {
                weatherResultsSection.innerHTML = `<p class="error-text">Пожалуйста, введите название города.</p>`;
                return;
            }
            
            weatherResultsSection.innerHTML = `<p class="loading-text">Получение прогноза для ${cityName}...</p>`;
            try {
                const response = await fetch(`/api/weather/${encodeURIComponent(cityName)}`);
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: "Неизвестная ошибка сервера" })); // попытка получить джсон ошибки
                    throw new Error(errorData.detail || `Ошибка: ${response.status}`);
                }
                
                const data = await response.json();
                displayWeather(data);
                
            } catch (error) {
                console.error('Ошибка при получении погоды:', error);
                weatherResultsSection.innerHTML = `<p class="error-text">Не удалось загрузить погоду: ${error.message}</p>`;
            }
        });
    }
    
    function displayWeather(data) {
        const { city_info, weather } = data;
        if (!weather || !weather.daily || !weather.current_weather) {
            weatherResultsSection.innerHTML = `<p class="error-text">Получены неполные данные о погоде для ${city_info.name}.</p>`;
            return;
        }
        
        // формируем само отображения в HTML
        let htmlContent = `
            <div class="weather-card current-weather-card">
                <div class="weather-card-header">
                    <h2>Погода в ${city_info.name}</h2>
                    <p class="sub-text">${city_info.admin1 ? city_info.admin1 + ', ' : ''}${city_info.country || ''}</p>
                </div>
                <div class="current-weather-details">
                    <div class="current-temp">
                        ${renderWeatherIcon(weather.current_weather.weathercode, weather.current_weather.is_day)}
                        <span>${Math.round(weather.current_weather.temperature)}°C</span>
                    </div>
                    <div class="current-description">
                        <p>${getWmoDescription(weather.current_weather.weathercode)}</p>
                        <p>Ветер: ${weather.current_weather.windspeed} км/ч</p>
                    </div>
                </div>
            </div>
            <h3>Прогноз на 7 дней:</h3>
            <div class="forecast-grid">
        `;
        
        weather.daily.time.forEach((dateStr, index) => {
            const dayData = {
                date: new Date(dateStr),
                max_temp: Math.round(weather.daily.temperature_2m_max[index]),
                min_temp: Math.round(weather.daily.temperature_2m_min[index]),
                weathercode: weather.daily.weathercode[index],
                sunrise: new Date(weather.daily.sunrise[index]),
                sunset: new Date(weather.daily.sunset[index]),
                precipitation: weather.daily.precipitation_sum[index],
                windspeed: weather.daily.windspeed_10m_max[index]
            };
            
            // определяем время суток, от этогго зависит иконка, но пока что всегда день
            const isDayForForecast = true;
            htmlContent += `
                    <div class="forecast-day-card">
                        <h4>${formatDate(dayData.date)}</h4>
                        <div class="forecast-icon">
                            ${renderWeatherIcon(dayData.weathercode, isDayForForecast)}
                        </div>
                        <p class="temps">
                            <span class="max-temp">${dayData.max_temp}°C</span> / 
                            <span class="min-temp">${dayData.min_temp}°C</span>
                        </p>
                        <p class="desc-small">${getWmoDescription(dayData.weathercode)}</p>
                        <p class="extra-info">
                            <img src="/static/icons/sunrise.svg" alt="Sunrise" class="inline-icon"> ${formatTime(dayData.sunrise)}
                            <img src="/static/icons/sunset.svg" alt="Sunset" class="inline-icon"> ${formatTime(dayData.sunset)}
                        </p>
                        <p class="extra-info">
                            <img src="/static/icons/droplet.svg" alt="Precipitation" class="inline-icon"> ${dayData.precipitation} mm
                            <img src="/static/icons/wind.svg" alt="Wind" class="inline-icon"> ${dayData.windspeed} км/ч
                        </p>
                    </div>
                `;
        });
        
        htmlContent += '</div>';
        weatherResultsSection.innerHTML = htmlContent;  
    }
    
    function getWmoDescription(code) {
        return WMO_CODES[code] ? WMO_CODES[code].description : `Код ${code}`;
    }
    
    function renderWeatherIcon(code, isDay = true) {
        const wmoEntry = WMO_CODES[code];
        let iconClass = "weather-icon color-primary-text";
        if (wmoEntry) {
            const iconName = isDay ? wmoEntry.icon_day : wmoEntry.icon_night;
            if (iconName) {
                // убедимся что путь правильный
                return `<img src="/static/icons/${iconName}" alt="${wmoEntry.description}" class="weather-icon">`;
            }
        }
        return `<img src="/static/icons/help-circle.svg"" alt="${wmoEntry.description}" class="weather-icon">`; // временно заглушка
    }
    
    function formatDate(dateObj) {
        return dateObj.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' });
    }
    
    function formatTime(dateObj) {
        return dateObj.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }
});