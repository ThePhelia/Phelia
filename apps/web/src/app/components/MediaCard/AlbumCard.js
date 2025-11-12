import { jsx as _jsx } from "react/jsx-runtime";
import { forwardRef } from 'react';
import MediaCardBase from '@/app/components/MediaCard/MediaCardBase';
const AlbumCard = forwardRef((props, ref) => _jsx(MediaCardBase, { ref: ref, ...props }));
AlbumCard.displayName = 'AlbumCard';
export default AlbumCard;
