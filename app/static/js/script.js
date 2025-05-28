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
    // элемент для отображения подсказок автодопа и добавим в html если его не было
    let autocompleteResultsDiv = document.getElementById('autocomplete-results');
    if (!autocompleteResultsDiv) {
        autocompleteResultsDiv = document.createEvent('div');
        autocompleteResultsDiv.id =  'autocomplete-results';
        autocompleteResultsDiv.className = 'autocomplete-suggestions'; // для стилей
        cityInput.parentNode.insertBefore(autocompleteResultsDiv, cityInput.nextSibling);
    }
    
    let autocompleteDebounceTimer;
    const DEBOUNCE_DELAY = 100; // mc
    
    if (cityInput) {
        cityInput.addEventListener('input', () => {
            clearTimeout(autocompleteDebounceTimer);
            const query = cityInput.value.trim();
            
            if (query.length < 2) { // поиск от 2-х символов
                autocompleteResultsDiv.innerHTML = '';
                autocompleteResultsDiv.style.display = 'none';
                return;
            }
            
            autocompleteDebounceTimer = setTimeout(async () => {
                try {
                    const response = await fetch(`/api/autocomplete/cities?query=${encodeURIComponent(query)}`);
                    if (!response.ok) {
                        // при ошибке не будем уведомлять об этом, а просто подсказок не будет
                        console.error(`Ошибка сети при автодополнении: ${response.status}`);
                        autocompleteResultsDiv.innerHTML = '';
                        autocompleteResultsDiv.style.display = 'none';
                        return;
                    }
                    const cities = await response.json();
                    displayAutocompleteResults(cities);
                } catch (error) {
                    console.log('Ошибка автодополнения:', error);
                    autocompleteResultsDiv.innerHTML = '';
                    autocompleteResultsDiv.style.display = 'none';
                }
            }, DEBOUNCE_DELAY);
        });
        
        // фокус теряется и автодоп скрывается если не нажали на список
        cityInput.addEventListener('blur', () => {
            // задержка чтобы можно успеть кликнуть по элементу списка
            setTimeout(() => {
                if (!autocompleteResultsDiv.matches(':hover')) { // если мышка над списком
                    autocompleteResultsDiv.style.display = 'none';
                }
            }, 150);
        });
        
        cityInput.addEventListener('focus', () => {
            // если текст есть, то пробуе мпоказать
            if (cityInput.value.trim().length >= 2 && autocompleteResultsDiv.children.length() > 0) {
                autocompleteResultsDiv.style.display = 'block';
            }
        });
    }
    
    function displayAutocompleteResults(cities) {
        autocompleteResultsDiv.innerHTML = ''; // предыдущие рез очищаем
        if (cities && cities.length > 0) {
            const u1 = document.createElement('u1');
            cities.forEach(cityData => {
                const li = document.createElement('li');
                let displayText = cityData.name;
                if (cityData.admin1 && cityData.admin1 != cityData.name) { // если регион = городу, то регион не пишем
                    displayText += `, ${cityData.admin1}`;
                }
                if (cityData.country) {
                    displayText += `, ${cityData.country}`;
                }
                li.textContent = displayText;
                
                // сохраняем координаты и точное имя, в data-атрибутах
                li.dataset.cityNmae = cityData.name;
                if (cityData.latitude !== undefined && cityData.longitude !== undefined) {
                    li.dataset.lat = cityData.latitude;
                    li.dataset.lon = cityData.longitude;
                }
                
                li.addEventListener('mousedown', () => {
                    cityInput.value = cityData.name; // вставка только города для поиска
                    autocompleteResultsDiv.innerHTML = '';
                    autocompleteResultsDiv.style.display = 'none';
                    // автоматич сразу поиск
                    fetchWeatherForSelectedCity(cityData.name, cityData.latitude, cityData.longitude);
                });
                u1.appendChild(li);
            });
            autocompleteResultsDiv.appendChild(u1);
            autocompleteResultsDiv.style.display = 'block';
        } else {
            autocompleteResultsDiv.style.display = 'none';
        }
    }
    
    async function fetchWeatherForSelectedCity(cityName, lat, lon) {
        weatherResultsSection.innerHTML = `<p class="loading-text">Получение прогноза для ${cityName}...</p>`;
        
        let apiUrl = `/api/weather/${encodeURIComponent(cityName)}`;
        // если точные координаты есть то добавляем как query
        if (lat !== undefined && lon !== undefined) {
            apiUrl += `?lat=${lat}&lon=${lon}`;
        }
        
        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Неизвестная ошибка сервера"}));
                throw new Error(errorData.detail ||  `Ошибка: ${response.status}`);
            }
            const data = await response.json();
            displayWeather(data);
        } catch (error) {
            console.error('Ошибка при получении погоды:', error);
        weatherResultsSection.innerHTML = `<p class="error-text">Не удалось загрузить погоду: ${error.message}</p>`;
        }
    }
    if (weatherForm) {
        weatherForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // блокируем стандартную отправку формы
            const cityNameFromInput = cityInput.value.trim();
            
            if (!cityNameFromInput) {
                weatherResultsSection.innerHTML = `<p class="error-text">Пожалуйста, введите название города.</p>`;
                return;
            }
            
         fetchWeatherForSelectedCity(cityNameFromInput, undefined, undefined);
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