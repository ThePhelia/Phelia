import { fireEvent, screen, waitFor } from "@testing-library/react";
import DetailDialog from "@/app/components/Detail/DetailDialog";
import type { DetailResponse } from "@/app/lib/types";
import { renderWithProviders } from "@/app/test-utils";
import type { MetaDetail } from "@/app/types/meta";

const { useDetailsMock, useMetaDetailMock, fetchForQueryMock, detailContentSpy, toastMock } = vi.hoisted(() => ({
  useDetailsMock: vi.fn(),
  useMetaDetailMock: vi.fn(),
  fetchForQueryMock: vi.fn(),
  detailContentSpy: vi.fn(({ detail }: { detail: DetailResponse }) => (
    <div data-testid="detail-content">{detail.title}</div>
  )),
  toastMock: Object.assign(vi.fn(), { error: vi.fn() }),
}));

vi.mock("@/app/lib/api", () => ({
  useDetails: useDetailsMock,
  useMetaDetail: useMetaDetailMock,
}));

vi.mock("@/app/components/Detail/DetailContent", () => ({
  default: detailContentSpy,
}));

vi.mock('sonner', () => ({
  toast: toastMock,
}));

vi.mock('@/app/stores/torrent-search', () => ({
  useTorrentSearch: (selector?: (state: { fetchForQuery: typeof fetchForQueryMock }) => unknown) => {
    const state = { fetchForQuery: fetchForQueryMock } as const;
    return selector ? selector(state) : state;
  },
}));

describe("DetailDialog", () => {
  const detail: DetailResponse = {
    id: "42",
    kind: "movie",
    title: "The Hitchhiker",
    overview: "A sci-fi classic.",
    similar: [],
    recommended: [],
  };

  beforeEach(() => {
    useDetailsMock.mockReset();
    useMetaDetailMock.mockReset();
    fetchForQueryMock.mockReset();
    detailContentSpy.mockClear();
    toastMock.mockClear();
    toastMock.error.mockClear();
  });

  it("renders skeleton while loading", () => {
    useDetailsMock.mockReturnValue({ data: undefined, isLoading: true, isError: false });
    useMetaDetailMock.mockReturnValue({ data: undefined, isLoading: false, isError: false });
    renderWithProviders(<DetailDialog kind="movie" id="42" open onOpenChange={() => {}} />);

    expect(document.body.querySelectorAll(".animate-shimmer")).not.toHaveLength(0);
    expect(detailContentSpy).not.toHaveBeenCalled();
  });

  it("shows error message when request fails", () => {
    useDetailsMock.mockReturnValue({ data: undefined, isLoading: false, isError: true });
    useMetaDetailMock.mockReturnValue({ data: undefined, isLoading: false, isError: false });
    renderWithProviders(<DetailDialog kind="movie" id="42" open onOpenChange={() => {}} />);

    expect(screen.getByText(/failed to load details/i)).toBeInTheDocument();
  });

  it("renders detail content when data resolved", () => {
    useDetailsMock.mockReturnValue({ data: detail, isLoading: false, isError: false });
    useMetaDetailMock.mockReturnValue({ data: undefined, isLoading: false, isError: false });
    renderWithProviders(<DetailDialog kind="movie" id="42" open onOpenChange={() => {}} />);

    expect(detailContentSpy).toHaveBeenCalledWith({ detail }, expect.anything());
    expect(screen.getByTestId("detail-content")).toHaveTextContent(detail.title);
  });

  it("renders meta detail view when provider is present", async () => {
    useDetailsMock.mockReturnValue({ data: undefined, isLoading: false, isError: false });
    const metaDetail: MetaDetail = {
      type: 'movie',
      title: 'Blade Runner',
      year: 1982,
      poster: 'https://example.com/poster.jpg',
      synopsis: 'A replicant hunter faces his past.',
      genres: ['Sci-Fi'],
      runtime: 117,
      rating: 8.4,
      cast: [{ name: 'Harrison Ford', character: 'Deckard' }],
      canonical: {
        query: 'Blade Runner 1982',
        movie: { title: 'Blade Runner', year: 1982 },
      },
    };
    useMetaDetailMock.mockReturnValue({ data: metaDetail, isLoading: false, isError: false });
    fetchForQueryMock.mockResolvedValue(undefined);

    renderWithProviders(
      <DetailDialog kind="movie" id="101" provider="tmdb" open onOpenChange={() => {}} />
    );

    expect(screen.getByText('Blade Runner')).toBeInTheDocument();
    const button = screen.getByRole('button', { name: /find torrents/i });
    expect(button).toBeInTheDocument();

    fireEvent.click(button);
    await waitFor(() => expect(fetchForQueryMock).toHaveBeenCalled());
  });
});
