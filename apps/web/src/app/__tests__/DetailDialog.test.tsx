import { screen } from "@testing-library/react";
import DetailDialog from "@/app/components/Detail/DetailDialog";
import type { DetailResponse } from "@/app/lib/types";
import { renderWithProviders } from "@/app/test-utils";

const useDetailsMock = vi.fn();
const detailContentSpy = vi.fn(({ detail }: { detail: DetailResponse }) => (
  <div data-testid="detail-content">{detail.title}</div>
));

vi.mock("@/app/lib/api", () => ({
  useDetails: useDetailsMock,
}));

vi.mock("@/app/components/Detail/DetailContent", () => ({
  default: detailContentSpy,
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
    detailContentSpy.mockClear();
  });

  it("renders skeleton while loading", () => {
    useDetailsMock.mockReturnValue({ data: undefined, isLoading: true, isError: false });
    renderWithProviders(<DetailDialog kind="movie" id="42" open onOpenChange={() => {}} />);

    expect(document.body.querySelectorAll(".animate-shimmer")).not.toHaveLength(0);
    expect(detailContentSpy).not.toHaveBeenCalled();
  });

  it("shows error message when request fails", () => {
    useDetailsMock.mockReturnValue({ data: undefined, isLoading: false, isError: true });
    renderWithProviders(<DetailDialog kind="movie" id="42" open onOpenChange={() => {}} />);

    expect(screen.getByText(/failed to load details/i)).toBeInTheDocument();
  });

  it("renders detail content when data resolved", () => {
    useDetailsMock.mockReturnValue({ data: detail, isLoading: false, isError: false });
    renderWithProviders(<DetailDialog kind="movie" id="42" open onOpenChange={() => {}} />);

    expect(detailContentSpy).toHaveBeenCalledWith({ detail });
    expect(screen.getByTestId("detail-content")).toHaveTextContent(detail.title);
  });
});
