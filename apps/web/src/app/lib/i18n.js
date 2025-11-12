import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
const resources = {
    en: {
        translation: {
            common: {
                searchPlaceholder: 'Search movies, series, or music...',
                viewDetails: 'View details',
                play: 'Play',
                resume: 'Resume',
                download: 'Download',
                addToList: 'Add to list',
                removeFromList: 'Remove from list',
                retry: 'Retry',
                close: 'Close',
                cancel: 'Cancel',
                confirm: 'Confirm',
                loading: 'Loading',
                seeAll: 'See all',
            },
            sections: {
                home: 'Home',
                movies: 'Movies',
                tv: 'TV Shows',
                music: 'Music',
                library: 'My Library',
                downloads: 'Downloads',
                settings: 'Settings',
            },
            filters: {
                year: 'Year',
                genre: 'Genre',
                language: 'Language',
                country: 'Country',
                rating: 'Rating',
                sort: 'Sort',
                providers: 'Providers',
                type: 'Type',
                style: 'Style',
                artist: 'Artist',
                clear: 'Clear filters',
            },
            detail: {
                overview: 'Overview',
                cast: 'Cast',
                crew: 'Crew',
                seasons: 'Seasons',
                tracks: 'Track list',
                related: 'Related',
                availability: 'Availability',
                streams: 'Streams',
                torrents: 'Torrents',
            },
            settings: {
                general: 'General',
                appearance: 'Appearance',
                services: 'Services',
                theme: 'Theme',
                language: 'Language',
                system: 'System',
                dark: 'Dark',
                light: 'Light',
            },
        },
    },
};
if (!i18n.isInitialized) {
    void i18n
        .use(initReactI18next)
        .init({
        resources,
        lng: 'en',
        fallbackLng: 'en',
        interpolation: { escapeValue: false },
        ns: ['translation'],
        defaultNS: 'translation',
    })
        .catch((error) => {
        // eslint-disable-next-line no-console
        console.error('Failed to initialize i18n', error);
    });
}
export default i18n;
