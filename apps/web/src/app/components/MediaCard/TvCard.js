import { jsx as _jsx } from "react/jsx-runtime";
import { forwardRef } from 'react';
import MediaCardBase from '@/app/components/MediaCard/MediaCardBase';
const TvCard = forwardRef((props, ref) => _jsx(MediaCardBase, { ref: ref, ...props }));
TvCard.displayName = 'TvCard';
export default TvCard;
