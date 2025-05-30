document.addEventListener('DOMContentLoaded', () => {
    // динамич обновление года
    const currentYearSpan = document.getElementById('currentYear')
    if (currentYearSpan) {
        currentYearSpan.textContent = new Date().getFullYear();
    }
    
    const weatherForm = document.getElementById('weatherForm')
    const cityInput = document.getElementById('city')
    const weatherCardsPlaceholder = document.getElementById('weather-cards-placeholder');
    // от main.py 
    const WMO_CODES = typeof WMO_CODES_FROM_SERVER !== "undefined" ? WMO_CODES_FROM_SERVER : {};
    // элемент для отображения подсказок автодопа и добавим в html если его не было
    let autocompleteResultsDiv = document.getElementById('autocomplete-results');
    if (!autocompleteResultsDiv) {
        autocompleteResultsDiv = document.createElement('div');
        autocompleteResultsDiv.id =  'autocomplete-results';
        autocompleteResultsDiv.className = 'autocomplete-suggestions'; // для стилей
        cityInput.parentNode.insertBefore(autocompleteResultsDiv, cityInput.nextSibling);
    }
    
    let autocompleteDebounceTimer;
    const DEBOUNCE_DELAY = 100; // mc
    let activeSuggestionIndex = -1; // индекс выделенного элемента в списке автодопа
    
    const lastCitySuggestionContainer = document.getElementById('last-city-suggestion');
    const lastCityNameSpan = document.getElementById('last-city-name');
    const showLastCityButton = document.getElementById('show-last-city-weather');
    
    const weatherMapContainer = document.getElementById('weather-map-container');
    const mapElement = document.getElementById('map');
    let mapInstance = null; // хранит экземпляр класса карты Leaflet
    let currentMapMarker = null;
    
    // сохранени последнего города
    function saveLastSearchedCity(cityInfo) {
        // полностью инфо сохраняем, чтобы при восстановлении был корректный город
        if (cityInfo && cityInfo.name && cityInfo.latitude !== undefined && cityInfo.longitude !== undefined) {
            localStorage.setItem('lastSearchedCityDetails', JSON.stringify(cityInfo));
        }
    }
    
    // загрущка и отображения предложения этого последнего города
    function loadAndShowLastCitySuggestion() {
        const lastCityDetailString = localStorage.getItem('lastSearchedCityDetails');
        if (lastCityDetailString && lastCitySuggestionContainer && lastCityNameSpan && showLastCityButton) {
            try {
                const cityDetails = JSON.parse(lastCityDetailString);
                let displayText = cityDetails.name;
                if (cityDetails.admin1 && cityDetails.admin1 !== cityDetails.name) {
                    displayText += `, ${cityDetails.admin1}`;
                }
                if (cityDetails.country) {
                    displayText += `, ${cityDetails.country}`;
                }
                lastCityNameSpan.textContent = displayText;
                lastCitySuggestionContainer.style.display = 'block'; // показываем блок
                
                showLastCityButton.onclick = () => {
                    // для обратной связи визуальной, заполняем поле ввода городом
                    cityInput.value = cityDetails.name;
                    // запрос погоду по координатам
                    fetchWeatherForSelectedCity(cityDetails.name, cityDetails.latitude, cityDetails.longitude, cityDetails.admin1, cityDetails.country);
                    lastCitySuggestionContainer.style.display = 'none'; // скрываем после клика
                };
            } catch (e) {
                console.error("Ошибка при разборе lastSearchedCityDetails из localStorage:", e);
                localStorage.removeItem('lastSearchedCityDetails');
            }
        } else if (lastCitySuggestionContainer) {
            lastCitySuggestionContainer.style.display = 'none'; //  скрываем при отсутсвии данных
        }
    }
    
    loadAndShowLastCitySuggestion(); // при загрузке страницы
    
    if (cityInput) {
        cityInput.addEventListener('input', () => {
            clearTimeout(autocompleteDebounceTimer);
            activeSuggestionIndex = -1; // при новом вводе сброс индекса
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
            if (cityInput.value.trim().length >= 2 && autocompleteResultsDiv.children.length > 0  && autocompleteResultsDiv.querySelector('ul')) {
                autocompleteResultsDiv.style.display = 'block';
            }
        });
        
        // обработчик нажатия кнопок при вводе
        cityInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === 'Escape') {
                const suggestionList = autocompleteResultsDiv.querySelector('ul');
                const suggestionVisible = autocompleteResultsDiv.style.display === 'block' && suggestionList && suggestionList.children.length > 0;
                if (e.key === 'Escape') {
                    if (suggestionVisible) {
                        e.preventDefault(); // блок других действия для данной кнопки
                        autocompleteResultsDiv.style.display = 'none';
                        activeSuggestionIndex = -1;
                        cityInput.blur();
                    }
                    return;
                }
                
                if (!suggestionVisible) {
                    // если ентер при закрытом допе, то запрос просто отправляется как обычно
                    // сработает submit обработчик
                    return;
                }
                
                const items = suggestionList.querySelectorAll('li');
                if (!items.length && e.key !== 'Enter') {
                    return;
                }
                
                switch (e.key) {
                    case 'ArrowDown':
                        e.preventDefault(); // скролл блокируем
                        activeSuggestionIndex++;
                        if (activeSuggestionIndex >= items.length) {
                            activeSuggestionIndex = 0;
                        }
                        updateSuggestionHighlight(items);
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        activeSuggestionIndex--;
                        if (activeSuggestionIndex < 0) {
                            activeSuggestionIndex = items.length - 1;
                        }
                        updateSuggestionHighlight(items);
                        break;
                    case 'Enter':
                        e.preventDefault();
                        if (activeSuggestionIndex > -1 && items[activeSuggestionIndex]) {
                            items[activeSuggestionIndex].dispatchEvent(new Event('mousedown')); // имитация клика
                        } else {
                            // если нажали, но ничего не выделено, а может списко и пуст, то скрываем и отправляем запрос
                            autocompleteResultsDiv.style.display = 'none';
                            activeSuggestionIndex =-1;
                            if (cityInput.value.trim()) { // убедимся что есть что отправлять
                                weatherForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                            }
                        }
                        break;
                }
            }
        });
    }
    
    function updateSuggestionHighlight(items) {
        items.forEach((item, index) => {
            if (index === activeSuggestionIndex) {
                item.classList.add('active-suggestion');
                // прокрутка в элементу если не видим
                item.scrollIntoView({ behavior: 'smooth', block: 'nearest'});
            } else {
                item.classList.remove('active-suggestion');
            }
        })
    }
    
    function displayAutocompleteResults(cities) {
        autocompleteResultsDiv.innerHTML = ''; // предыдущие рез очищаем
        activeSuggestionIndex = -1;
        if (cities && cities.length > 0) {
            const ul = document.createElement('ul');
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
                li.dataset.cityName = cityData.name;
                if (cityData.latitude !== undefined && cityData.longitude !== undefined) {
                    li.dataset.lat = cityData.latitude;
                    li.dataset.lon = cityData.longitude;
                }
                
                li.addEventListener('mousedown', () => {
                    cityInput.value = cityData.name; // вставка только города для поиска
                    autocompleteResultsDiv.innerHTML = '';
                    autocompleteResultsDiv.style.display = 'none';
                    // автоматич сразу поиск
                    fetchWeatherForSelectedCity(cityData.name, cityData.latitude, cityData.longitude, cityData.admin1, cityData.country);
                });
                ul.appendChild(li);
            });
            autocompleteResultsDiv.appendChild(ul);
            autocompleteResultsDiv.style.display = 'block';
        } else {
            autocompleteResultsDiv.style.display = 'none';
        }
    }
    
    async function fetchWeatherForSelectedCity(baseName, lat, lon, admin1, country) {
        let displayNameForLoading = baseName;
        if (admin1 && admin1 !== baseName) {
            displayNameForLoading += `, ${admin1}`;
        }
        if (country) {
            displayNameForLoading += `, ${country}`;
        }
        if (weatherCardsPlaceholder) {
            weatherCardsPlaceholder.innerHTML = `<p class="loading-text">Получение прогноза для ${displayNameForLoading}...</p>`;
        }
        
        let apiUrl = `/api/weather/${encodeURIComponent(baseName)}`;

        const queryParams = new URLSearchParams();
        if (lat !== undefined && lon !== undefined) {
            queryParams.append('lat', lat);
            queryParams.append('lon', lon);
            // если есть точные координаты, то передаем и описание города
            if (baseName) {
                queryParams.append('selected_name', baseName);
            }
            if (admin1) {
                queryParams.append('selected_admin1', admin1);
            }
            if (country) {
                queryParams.append('selected_country', country);
            }
        }
        if (queryParams.toString()) {
            apiUrl += `?${queryParams.toString()}`;
        }
        
        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Неизвестная ошибка сервера"}));
                throw new Error(errorData.detail ||  `Ошибка: ${response.status}`);
            }
            const data = await response.json();
            displayWeather(data);
            
            // отображаем карту после получения погоды
            if (data && data.city_info && data.city_info.latitude !== undefined && data.city_info.longitude !== undefined) {
                if (weatherMapContainer) {
                    weatherMapContainer.style.display = 'block';
                }
                initOrUpdateMap(data.city_info, data.weather.current_weather); // передаем инфо о городе и текущую погоду
            } else {
                if (weatherMapContainer) {
                    weatherMapContainer.style.display = 'none'; // без координат скрываем
                }
            }
            // сохраняем последний город
            if (data && data.city_info) {
                saveLastSearchedCity(data.city_info)
                // обновляем предложение, чтобы был уже другой город
            }
            
            // скрываем недавний поиск после успешного нового
            if (lastCitySuggestionContainer) {
                lastCitySuggestionContainer.style.display = 'none';
            }
        } catch (error) {
            console.error('Ошибка при получении погоды:', error);
            //.weatherResultsSection.innerHTML = `<p class="error-text">Не удалось загрузить погоду: ${error.message}</p>`;
            if (weatherMapContainer) {
                weatherMapContainer.style.display = 'none';
            }
        }
    }
    
    function initOrUpdateMap(cityInfo, currentWeather) {
        const lat = cityInfo.latitude;
        const lon = cityInfo.longitude;
        const zoomLevel = 10;
        
        if (!mapElement) return;
        
        if (!mapInstance) {
            // инициализируем карту если ещё нет
            mapInstance = L.map(mapElement).setView([lat, lon], zoomLevel)
            // добавление тайлов (подложки для карты)
            L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(mapInstance);
        } else {
            // карта есть и просто перемещаем вид
            mapInstance.setView([lat, lon], zoomLevel);
        }
        
        // старый маркер удаляем и добавляем новый
        if (currentMapMarker) {
            mapInstance.removeLayer(currentMapMarker);
        }
        currentMapMarker = L.marker([lat, lon]).addTo(mapInstance);
        
        // контент для hover маркера
        let popupContent = `<b>${cityInfo.name}</b>`;
        if (currentWeather) {
            const temp = Math.round(currentWeather.temperature)
            const description = getWmoDescription(currentWeather.weathercode); // своя функция в js
            popupContent += `<br>${temp}°C, ${description}`;
        }
        
        currentMapMarker.bindPopup(popupContent).openPopup(); // сразу открываем hover
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
        if (weatherCardsPlaceholder) {
            weatherCardsPlaceholder.innerHTML = htmlContent; // перезаписываем только карточку погоды, карту не трогаем
        } else {
            console.error("Элемент #weather-cards-placeholder не найден!")
        }
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