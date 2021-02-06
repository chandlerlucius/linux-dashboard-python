
const handleTabs = function() {
    document.querySelectorAll('.tab-button').forEach(function(tab) {
        tab.addEventListener('click', tabClick);
    });
}

const tabClick = function() {
    document.querySelectorAll('.tab').forEach(function(tab) {
        tab.classList.add('hidden');
    });
    document.getElementById(this.id + '-div').classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', function() {
    handleTabs();
});