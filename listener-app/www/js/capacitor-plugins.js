// GoGospelNow Listener App - Main JavaScript
// Capacitor plugin imports are handled by the native bridge

const KeepAwake = {
    keepAwake: async () => {
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.KeepAwake) {
            return await window.Capacitor.Plugins.KeepAwake.keepAwake();
        }
        // Fallback for web/testing
        console.log('KeepAwake: keepAwake() called (web fallback)');
        return { isKeepingAwake: true };
    },
    allowSleep: async () => {
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.KeepAwake) {
            return await window.Capacitor.Plugins.KeepAwake.allowSleep();
        }
        // Fallback for web/testing
        console.log('KeepAwake: allowSleep() called (web fallback)');
        return { isKeepingAwake: false };
    },
    isKeptAwake: async () => {
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.KeepAwake) {
            return await window.Capacitor.Plugins.KeepAwake.isKeptAwake();
        }
        return { isKeptAwake: false };
    }
};

// Export for use in HTML
window.KeepAwake = KeepAwake;
