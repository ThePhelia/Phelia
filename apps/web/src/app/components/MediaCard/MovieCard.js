import { jsx as _jsx } from "react/jsx-runtime";
import { forwardRef } from 'react';
import MediaCardBase from '@/app/components/MediaCard/MediaCardBase';
const MovieCard = forwardRef((props, ref) => (_jsx(MediaCardBase, { ref: ref, ...props })));
MovieCard.displayName = 'MovieCard';
export default MovieCard;
