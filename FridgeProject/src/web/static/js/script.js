document.addEventListener('DOMContentLoaded', fetchData);

function fetchData() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            updateDashboard(data);
            const now = new Date();
            document.getElementById('last-updated').textContent = 'Last updated: ' + now.toLocaleTimeString();
        })
        .catch(error => console.error('Error fetching data:', error));
}

function updateDashboard(data) {
    // 1. Inventory Grid
    const invGrid = document.getElementById('inventory-grid');
    invGrid.innerHTML = '';

    // Group items by label
    const groups = {};
    if (data.items) {
        data.items.forEach(item => {
            if (!groups[item.label]) {
                groups[item.label] = [];
            }
            groups[item.label].push(item);
        });
    }

    if (Object.keys(groups).length === 0) {
        invGrid.innerHTML = '<p>Fridge is empty.</p>';
    } else {
        // Create card for each group
        for (const [label, items] of Object.entries(groups)) {
            // Sort by latest confirmed (desc)
            items.sort((a, b) => new Date(b.last_confirmed) - new Date(a.last_confirmed));
            const mainItem = items[0]; // Most recent
            const count = items.length;

            // Get crop path: "static/crops/filename.jpg" -> "/static/crops/filename.jpg"
            let imgSrc = mainItem.crop_path;
            if (imgSrc) {
                if (!imgSrc.startsWith('/')) {
                    imgSrc = '/' + imgSrc;
                }
            } else {
                // Fallback to full image if no crop? Or placeholder
                imgSrc = 'https://via.placeholder.com/150?text=' + encodeURIComponent(label);
            }

            const div = document.createElement('div');
            div.className = 'inventory-card';

            div.innerHTML = `
                <img src="${imgSrc}" alt="${label}" onerror="this.onerror=null;this.src='https://via.placeholder.com/150?text=Error';">
                <h3>${label}</h3>
                <span class="count-badge">${count} item${count > 1 ? 's' : ''}</span>
                <span class="time-info">Seen: ${new Date(mainItem.last_confirmed).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
            `;
            invGrid.appendChild(div);
        }
    }

    // 2. Recommendations
    const recList = document.getElementById('recommendations-list');
    recList.innerHTML = '';

    if (data.inventory && data.inventory.length > 0) {
        const criticalItems = data.inventory.filter(item => item.days_remaining < 3);
        const itemsToShow = criticalItems.length > 0 ? criticalItems : data.inventory.slice(0, 5);

        itemsToShow.forEach(item => {
            const div = document.createElement('div');
            div.className = 'recommendation-item';
            div.innerHTML = `
                <strong>Eat ${item.label}</strong><br>
                <small>Days left: ${item.days_remaining}</small>
            `;
            recList.appendChild(div);
        });
    } else {
        recList.innerHTML = '<p>Nothing urgent.</p>';
    }

    // 3. Shopping List
    const shopList = document.getElementById('missing-list');
    shopList.innerHTML = '';

    if (data.missing && data.missing.length > 0) {
        data.missing.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            shopList.appendChild(li);
        });
    } else {
        shopList.innerHTML = '<li>Nothing missing!</li>';
    }
}

// Poll every 5 seconds
setInterval(fetchData, 5000);
