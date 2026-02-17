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
    // 1. Recommendations
    const recList = document.getElementById('recommendations-list');
    recList.innerHTML = '';

    if (data.inventory.length === 0) {
         recList.innerHTML = '<p>No food detected.</p>';
    } else {
        // Filter critical items (less than 3 days remaining)
        const criticalItems = data.inventory.filter(item => item.days_remaining < 3);
        // Show critical items, or top 3 if no critical items
        const itemsToShow = criticalItems.length > 0 ? criticalItems : data.inventory.slice(0, 3);

        itemsToShow.forEach(item => {
            const div = document.createElement('div');
            div.className = 'recommendation-item';
            div.innerHTML = `
                <strong>Eat ${item.label}</strong><br>
                <small>In fridge: ${item.days_in_fridge}d | Expires in: ${item.days_remaining}d</small>
            `;
            recList.appendChild(div);
        });

        if (itemsToShow.length === 0 && data.inventory.length > 0) {
             recList.innerHTML = '<p>Everything is fresh!</p>';
        }
    }

    // 2. Inventory
    const invGrid = document.getElementById('inventory-grid');
    invGrid.innerHTML = '';

    if (data.inventory.length === 0) {
        invGrid.innerHTML = '<p>Fridge is empty.</p>';
    }

    data.inventory.forEach(item => {
        const div = document.createElement('div');
        div.className = 'inventory-item';

        let imgSrc = item.image_path;
        // Adjust path for serving
        if (imgSrc && imgSrc.startsWith('images/')) {
            imgSrc = imgSrc.replace(/^images\//, '/images/');
        } else if (imgSrc && !imgSrc.startsWith('/') && !imgSrc.startsWith('http')) {
             imgSrc = '/images/' + imgSrc;
        }

        const statusClass = item.status === 'Critical' ? 'status-critical' : 'status-good';

        div.innerHTML = `
            <img src="${imgSrc}" alt="${item.label}" onerror="this.src='https://via.placeholder.com/60?text=?'">
            <div class="inventory-details">
                <h3>${item.label}</h3>
                <span class="status-badge ${statusClass}">${item.days_in_fridge} days old</span>
            </div>
        `;
        invGrid.appendChild(div);
    });

    // 3. Shopping List
    const shopList = document.getElementById('missing-list');
    shopList.innerHTML = '';

    if (data.missing.length === 0) {
        shopList.innerHTML = '<li>Nothing missing!</li>';
    } else {
        data.missing.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            shopList.appendChild(li);
        });
    }
}

// Poll every 5 seconds
setInterval(fetchData, 5000);
