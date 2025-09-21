import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MediaCardBase from "@/app/components/MediaCard/MediaCardBase";
import type { DiscoverItem } from "@/app/lib/types";
import { renderWithProviders } from "@/app/test-utils";

const { mutateAsync, navigateMock, toastSuccess, toastError, toastMock, fetchForItemMock } = vi.hoisted(() => {
  const mutateAsync = vi.fn();
  const navigateMock = vi.fn();
  const toastSuccess = vi.fn();
  const toastError = vi.fn();
  const toastMock = Object.assign(vi.fn(), {
    success: toastSuccess,
    error: toastError,
  });
  const fetchForItemMock = vi.fn();
  return { mutateAsync, navigateMock, toastSuccess, toastError, toastMock, fetchForItemMock };
});

vi.mock("sonner", () => ({
  toast: toastMock,
}));

vi.mock("@/app/lib/api", () => ({
  useMutateList: () => ({ mutateAsync }),
}));

vi.mock("@/app/stores/torrent-search", () => ({
  useTorrentSearch: (selector?: (state: { fetchForItem: typeof fetchForItemMock }) => unknown) =>
    selector ? selector({ fetchForItem: fetchForItemMock }) : { fetchForItem: fetchForItemMock },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useLocation: () => ({ pathname: "/movies" }),
  };
});

describe("MediaCardBase", () => {
  const item: DiscoverItem = {
    id: "123",
    kind: "movie",
    title: "Inception",
    year: 2010,
    subtitle: "Dream Heist",
    poster: "https://image.tmdb.org/t/p/original/inception.jpg",
    genres: ["Sci-Fi", "Thriller"],
    badges: ["HDR", "4K"],
    progress: 0.35,
    meta: { source: "tmdb" },
  };

  beforeEach(() => {
    mutateAsync.mockReset().mockResolvedValue(undefined);
    navigateMock.mockReset();
    toastMock.mockClear();
    toastSuccess.mockClear();
    toastError.mockClear();
    fetchForItemMock.mockReset();
  });

  it("renders media information and opens details when card clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MediaCardBase item={item} />);

    expect(screen.getByRole("heading", { name: item.title })).toBeInTheDocument();
    expect(screen.getByText("Sci-Fi, Thriller", { exact: false })).toBeInTheDocument();

    const detailsButton = screen
      .getAllByRole("button", { name: /details/i })
      .find((element) => element.tagName === "BUTTON");
    expect(detailsButton).toBeDefined();
    await user.click(detailsButton!);
    expect(navigateMock).toHaveBeenCalledWith(
      `/details/${item.kind}/${item.id}`,
      expect.objectContaining({
        state: { backgroundLocation: expect.objectContaining({ pathname: "/movies" }) },
      }),
    );
  });

  it("queues watchlist mutation and shows success toast", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MediaCardBase item={item} />);

    await user.click(screen.getByRole("button", { name: /add to watchlist/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        action: "add",
        list: "watchlist",
        item: { id: item.id, kind: item.kind },
      });
    });

    expect(navigateMock).not.toHaveBeenCalled();
    expect(toastMock.success).toHaveBeenCalledWith(`Added ${item.title} to your watchlist.`);
  });

  it("opens the torrent search dialog when download button clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MediaCardBase item={item} />);

    const downloadButton = screen.getByRole("button", { name: /torrent search/i });
    await user.click(downloadButton);

    expect(fetchForItemMock).toHaveBeenCalledWith({
      id: item.id,
      title: item.title,
      kind: item.kind,
      year: item.year,
    });
    expect(toastMock).not.toHaveBeenCalled();
  });
});
